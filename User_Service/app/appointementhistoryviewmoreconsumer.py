import json
import pika
import django
import os
import sys
from django.conf import settings

import logging
import time

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Import your models
from app.models import DoctorAvailability, UserProfile

logger = logging.getLogger("django")


def on_request(ch, method, properties, body):
    """Handle incoming requests to fetch user data."""
    request_data = json.loads(body)
    id = request_data.get("id")

    # logger.info(department)
    response = {}
    try:

        details = DoctorAvailability.objects.select_related("patient").get(id=id)

        History = {
            "id": details.id,
            "profile_pic": (
                details.patient.profile_pic.url if details.patient.profile_pic else None
            ),
            "first_name": details.patient.first_name,
            "last_name": details.patient.last_name,
            "gender": details.patient.gender,
            "blood_group": details.patient.blood_group,  # Convert Decimal to string
            "weight": str(details.patient.weight),
            "height": str(details.patient.height),
            "email": details.patient.email,
            "mobile_number": details.patient.mobile_number,
            "medical_report": str(details.patient.medical_report),
            "date_of_birth": str(details.patient.date_of_birth),
            "room_created": details.room_created,
            "meet_link": details.meet_link,
        }

    except UserProfile.DoesNotExist:
        response = {"error": "patient not found"}

    response = {"History": History}
    response_body = json.dumps(response)
    logger.info(
        f"Attempting to send response to reply_to queue: {properties.reply_to}, correlation_id: {properties.correlation_id}"
    )
    try:
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            body=response_body,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        )
        logger.info(
            f"Response sent to reply_to queue: {properties.reply_to}, correlation_id: {properties.correlation_id}"
        )
    except Exception as e:
        logger.error(f"Failed to publish response to reply_to queue: {str(e)}")
        raise
    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_user_service():
    """Start RabbitMQ consumer for user service."""
    rabbitmq_host = getattr(settings, "RABBITMQ_HOST", "rabbitmq")
    logger.info(f"Starting User_Service with RabbitMQ host: {rabbitmq_host}")

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=rabbitmq_host)
            )
            channel = connection.channel()

            channel.queue_declare(queue="appointment_history_viewmore", durable=True)

            channel.basic_consume(
                queue="appointment_history_viewmore", on_message_callback=on_request
            )
            logger.info(" [x] Waiting for user requests...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ not available, retrying in 5 seconds: {str(e)}")
            time.sleep(5)
        finally:
            if "channel" in locals():
                channel.close()
            if "connection" in locals():
                connection.close()


if __name__ == "__main__":
    start_user_service()
