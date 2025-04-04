import pika
import json
import time
import logging
import os
import django
import sys
from rest_framework import status

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
django.setup()

# Now import your models
from app.models import UserProfile, DoctorAvailability
from app.tasks import send_appointment_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("consumer.log"),  # Save logs to a file
        logging.StreamHandler(),  # Print logs to the console
    ],
)
logger = logging.getLogger(__name__)

# Test Django ORM setup
logger.info("Initializing consumer...")
try:
    user_count = UserProfile.objects.count()
    logger.info(f"Django ORM test successful: UserProfile count = {user_count}")
except Exception as e:
    logger.error(f"Django ORM setup failed: {str(e)}")


def connect_to_rabbitmq():
    """Retries RabbitMQ connection until successful"""
    retries = 15
    for i in range(retries):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
            )
            logger.info("Connected to RabbitMQ successfully")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"Retry {i+1}/{retries} - Waiting for RabbitMQ: {str(e)}")
            time.sleep(5)
    logger.error("Failed to connect to RabbitMQ after multiple retries")
    raise Exception("Failed to connect to RabbitMQ after multiple retries")


from django.db import transaction


def slotbooking(data):
    """Check if a doctor is available and update the slot status if booked"""
    doctor_email = data.get("doctor_email")
    date = data.get("date")
    slot = data.get("slot")
    patient_email = data.get("patient_email")
    amount = data.get("amount")

    logger.info(
        f"Processing booking: doctor={doctor_email}, date={date}, slot={slot}, patient={patient_email}"
    )

    try:
        doctor = UserProfile.objects.get(email=doctor_email, is_doctor=True)
        patient = UserProfile.objects.get(email=patient_email, is_doctor=False)
        logger.info(f"Found doctor: {doctor.email}, patient: {patient.email}")

        with transaction.atomic():
            availability = (
                DoctorAvailability.objects.select_for_update()
                .filter(doctor=doctor, date=date, slot=slot, is_available=True)
                .first()
            )
            logger.info(f"Availability query result: {availability}")

            if availability:
                availability.is_available = False
                availability.status = "Pending"
                availability.patient = patient
                availability.amount = amount
                availability.save()
                logger.info(
                    f"Slot updated: is_available={availability.is_available}, status={availability.status}"
                )

                to_email = patient.email
                subject = "Appointment Confirmation"
                message = f"Your appointment is confirmed. See you soon! Booking Date {date} at {slot}"
                send_appointment_email.delay(to_email, subject, message)
                logger.info(
                    f"Booked appointment for Dr. {doctor.first_name} on {date} at {slot}"
                )
                return {
                    "available": False,
                    "doctor_name": doctor.first_name,
                    "status": "Pending",
                }
            else:
                logger.warning(
                    f"No available slot for Dr. {doctor.first_name} on {date} at {slot}"
                )
                return {"error": "Doctor is not available"}
    except UserProfile.DoesNotExist:
        if not UserProfile.objects.filter(email=doctor_email, is_doctor=True).exists():
            logger.error(f"Doctor with email '{doctor_email}' not found")
            return {"error": "Doctor not found"}
        if not UserProfile.objects.filter(
            email=patient_email, is_doctor=False
        ).exists():
            logger.error(f"Patient with email '{patient_email}' not found")
            return {"error": "Patient not found"}
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {"error": f"Database connection failed: {str(e)}"}


def callback(ch, method, properties, body):
    """Handles incoming RabbitMQ messages"""
    try:
        data = json.loads(body.decode())
        logger.info(f"Received message: {data}")
        response = slotbooking(data)
        logger.info(f"Processed booking request: {response}")
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in received message")
        response = {"error": "Invalid JSON format"}
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        response = {"error": str(e)}

    try:
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=json.dumps(response).encode(),
        )
        logger.info(f"Sent response to {properties.reply_to}: {response}")
    except Exception as e:
        logger.error(f"Failed to send response: {str(e)}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer():
    """Starts RabbitMQ consumer and ensures connection recovery"""
    while True:
        try:
            logger.info("Connecting to RabbitMQ...")
            connection = connect_to_rabbitmq()
            channel = connection.channel()
            channel.queue_declare(queue="slotbooking", durable=True)

            # Test message for debugging (comment out after testing)
            test_data = json.dumps(
                {
                    "doctor_email": "doctor@example.com",
                    "patient_email": "patient@example.com",
                    "date": "2025-03-20",
                    "slot": "10:00",
                    "amount": "500",
                }
            )
            channel.basic_publish(
                exchange="", routing_key="slotbooking", body=test_data.encode()
            )
            logger.info("Published test message to slotbooking queue")

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue="slotbooking", on_message_callback=callback)

            logger.info(" [✔] Waiting for messages from Appointment Service...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection lost: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Consumer error: {e}. Restarting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    logger.info("Starting consumer... Waiting 5 seconds to ensure RabbitMQ is ready")
    time.sleep(5)
    start_consumer()
