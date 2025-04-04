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

logger = logging.getLogger("django")
from app.tasks import send_appointment_email


def on_request(ch, method, properties, body):
    request_data = json.loads(body)
    id = request_data.get("id")
    response = {}

    try:
        with transaction.atomic():
            room = DoctorAvailability.objects.get(id=id, isDelete=False)
            room.delete()
            response = {"message": "Slot Deleted"}

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        response = {"error": f"Database connection failed: {str(e)}"}

    if response:
        try:
            logger.info(
                f"Attempting to send response to {properties.reply_to} with correlation_id {properties.correlation_id}"
            )
            ch.basic_publish(
                exchange="",
                routing_key=properties.reply_to,
                body=json.dumps(response),
                properties=pika.BasicProperties(
                    correlation_id=properties.correlation_id
                ),
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
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=rabbitmq_host)
            )
            channel = connection.channel()

            channel.queue_declare(queue="slotdeleting", durable=True)

            channel.basic_consume(queue="slotdeleting", on_message_callback=on_request)
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
