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
from app.models import UserProfile, DoctorAvailability  #
from app.tasks import send_appointment_email

# Initialize Django ORM manually if needed


# 🔹 Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("consumer.log"),  # Save logs to a file
        logging.StreamHandler(),  # Print logs to the console
    ],
)
logger = logging.getLogger(__name__)
logger.info("hlo")


def connect_to_rabbitmq():
    """Retries RabbitMQ connection until successful"""
    retries = 15  # Increased retries to handle startup delays
    for i in range(retries):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    heartbeat=600,  # Keeps connection alive
                    blocked_connection_timeout=300,  # Prevents timeouts
                )
            )
            logging.info("Connected to RabbitMQ successfully.")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logging.warning(f"Retry {i+1}/{retries} - Waiting for RabbitMQ...")
            time.sleep(5)  # Wait before retrying
    logging.error("Failed to connect to RabbitMQ after multiple retries.")
    raise Exception("Failed to connect to RabbitMQ after multiple retries.")


from django.db import transaction


def check_doctor_availability(data):
    """Check if a doctor is available and update the slot status if booked"""
    doctor_email = data.get("doctor_email")
    date = data.get("date")
    slot = data.get("slot")
    patient_email = data.get("patient_email")

    try:
        doctor = UserProfile.objects.get(email=doctor_email, is_doctor=True)
        patient = UserProfile.objects.get(email=patient_email, is_doctor=False)

        with transaction.atomic():
            availability = (
                DoctorAvailability.objects.select_for_update()
                .filter(doctor=doctor, date=date, slot=slot, is_available=True)
                .first()
            )

            if availability:
                availability.is_available = False
                availability.status='Pending'
                availability.patient = patient
                availability.save()
                logging.info("hi")
                to_email = patient.email
                subject = "Appointment Confirmation"
                message = f"Your appointment is confirmed. See you soon! Booking Date {date} at {slot}"
                send_appointment_email.delay(to_email, subject, message)
                logging.info(
                    f"Booked appointment for Dr. {doctor.first_name} on {date} at {slot}."
                )
                return {
                    "available": False,
                    "doctor_name": doctor.first_name,
                    "status": "Booked",
                }
            else:
                logging.warning(
                    f"Doctor {doctor.first_name} is not available on {date} at {slot}."
                )
                return {"error": "Doctor is not available"}
    except UserProfile.DoesNotExist:
        if not UserProfile.objects.filter(email=doctor_email, is_doctor=True).exists():
            logging.error(f"Doctor with email '{doctor_email}' not found.")
            return {"error": "Doctor not found"}

        if not UserProfile.objects.filter(
            email=patient_email, is_doctor=False
        ).exists():
            logging.error(f"Patient with email '{patient_email}' not found.")
            return {"error": "Patient not found"}

    except Exception as e:
        logging.error(f"Database error: {e}")
        return {"error": "Database connection failed"}


def callback(ch, method, properties, body):
    """Handles incoming RabbitMQ messages"""
    try:
        data = json.loads(body)
        logging.info(f"Received message: {data}")
        response = check_doctor_availability(data)
    except json.JSONDecodeError:
        logging.error("Invalid JSON format in received message.")
        response = {"error": "Invalid JSON format"}
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        response = {"error": str(e)}

    ch.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        body=json.dumps(response),
    )

    ch.basic_ack(delivery_tag=method.delivery_tag)
    logging.info(f"Sent response: {response}")


def start_consumer():
    """Starts RabbitMQ consumer and ensures connection recovery"""
    while True:
        try:
            logging.info("Connecting to RabbitMQ...")
            connection = connect_to_rabbitmq()
            channel = connection.channel()
            channel.queue_declare(queue="check_doctor_availability")

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue="check_doctor_availability", on_message_callback=callback
            )

            logging.info(" [✔] Waiting for messages from Appointment Service...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logging.error(
                f"RabbitMQ connection lost: {e}. Reconnecting in 5 seconds..."
            )
            time.sleep(5)  # Wait and retry if RabbitMQ crashes

        except Exception as e:
            logging.error(f"Consumer error: {e}. Restarting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    logging.info("Starting consumer... Waiting 5 seconds to ensure RabbitMQ is ready.")
    time.sleep(5)  # Ensures RabbitMQ is ready before starting
    start_consumer()
