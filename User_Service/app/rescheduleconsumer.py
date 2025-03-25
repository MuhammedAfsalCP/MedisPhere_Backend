import json
import pika
import django
import os
import sys
from django.conf import settings
from django.db import transaction
import logging
import time
from datetime import datetime
# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Import your models
from app.models import DoctorAvailability, UserProfile
logger = logging.getLogger('django')
from app.tasks import send_appointment_email
def on_request(ch, method, properties, body):
    request_data = json.loads(body)
    id = request_data.get("id")
    date = request_data.get("date")
    slot = request_data.get("slot")
    patient_email = request_data.get("patient_email")
    response = {}

    if not id or not isinstance(id, int):
        response = {"error": "Invalid or missing ID"}
    elif not date:
        response = {"error": "Date is required"}
    else:
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            response = {"error": "Invalid date format. Use YYYY-MM-DD."}
    if not slot or not isinstance(slot, str):
        response = {"error": "Invalid or missing slot"}
    if not patient_email or not isinstance(patient_email, str):
        response = {"error": "Invalid or missing patient_email"}

    if response:
        if properties.reply_to:
            logger.info(f"Attempting to send response to {properties.reply_to} with correlation_id {properties.correlation_id}")
            ch.basic_publish(exchange="", routing_key=properties.reply_to, body=json.dumps(response),
                            properties=pika.BasicProperties(correlation_id=properties.correlation_id))
            logger.info(f"Response sent to {properties.reply_to}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        with transaction.atomic():
            logger.info(f"Fetching current room with id={id}")
            room = DoctorAvailability.objects.get(id=id, isDelete=False)
            logger.info(f"Current room fetched: id={room.id}, is_available={room.is_available}, status={room.status}, patient={room.patient}")

            logger.info(f"Fetching new updateroom for doctor={room.doctor.id}, date={date}, slot={slot}")
            updateroom = DoctorAvailability.objects.get(doctor=room.doctor, date=date, slot=slot)
            logger.info(f"New updateroom fetched: id={updateroom.id}, is_available={updateroom.is_available}, status={updateroom.status}")

            if room.id == updateroom.id:
                response = {"error": "Cannot reschedule to the same slot"}
            elif not updateroom.is_available:
                response = {"error": "Requested slot is already booked"}
            else:
                logger.info(f"Updating updateroom: is_available=False, status='Pending', patient={room.patient}, amount={room.amount}")
                updateroom.is_available = False
                updateroom.status = "Pending"
                updateroom.patient = room.patient
                updateroom.amount = room.amount
                updateroom.save()
                logger.info(f"Updateroom saved: id={updateroom.id}, is_available={updateroom.is_available}, status={updateroom.status}")
                updateroom_db = DoctorAvailability.objects.get(id=updateroom.id)
                logger.info(f"Updateroom from DB: id={updateroom_db.id}, is_available={updateroom_db.is_available}, status={updateroom_db.status}")

                logger.info(f"Updating room: is_available=True, status=None, patient=None")
                room.is_available = True
                room.status = None
                room.patient = None
                room.save()
                logger.info(f"Room saved: id={room.id}, is_available={room.is_available}, status={room.status}")
                room_db = DoctorAvailability.objects.get(id=room.id)
                logger.info(f"Room from DB: id={room_db.id}, is_available={room_db.is_available}, status={room_db.status}")

                logger.info(f"Rescheduled appointment for Dr. {room.doctor.first_name} from id={room.id} to id={updateroom.id} on {date} at {slot}")
                response = {"available": False, "message": "rescheduled"}

        to_email = patient_email
        if to_email:
            subject = "Appointment Confirmation"
            message = f"Reschedule is confirmed. See you soon! Booking Date {date} at {slot}"
            send_appointment_email.delay(to_email, subject, message)

    except DoctorAvailability.DoesNotExist:
        logger.error(f"DoctorAvailability not found for id={id} or doctor={room.doctor.id if 'room' in locals() else 'unknown'}, date={date}, slot={slot}")
        response = {"error": "Doctor availability not found for the given ID or slot"}
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        response = {"error": f"Database connection failed: {str(e)}"}

    if response:
        try:
            logger.info(f"Attempting to send response to {properties.reply_to} with correlation_id {properties.correlation_id}")
            ch.basic_publish(
                exchange="",
                routing_key=properties.reply_to,
                body=json.dumps(response),
                properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            )
            logger.info(f"Response sent to {properties.reply_to}")
        except Exception as e:
            logger.error(f"Failed to publish response: {str(e)}")
    
    ch.basic_ack(delivery_tag=method.delivery_tag)
def start_user_service():
    """Start RabbitMQ consumer for user service."""
    rabbitmq_host = getattr(settings, "RABBITMQ_HOST", "rabbitmq")
    logger.info(f"Starting User_Service with RabbitMQ host: {rabbitmq_host}")

    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
            channel = connection.channel()

            channel.queue_declare(queue="reschedule", durable=True)

            channel.basic_consume(queue="reschedule", on_message_callback=on_request)
            logger.info(" [x] Waiting for user requests...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ not available, retrying in 5 seconds: {str(e)}")
            time.sleep(5)
        finally:
            if 'channel' in locals():
                channel.close()
            if 'connection' in locals():
                connection.close()

if __name__ == "__main__":
    start_user_service()