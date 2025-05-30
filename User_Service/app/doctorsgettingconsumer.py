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
    department = request_data.get("department")
    logger.info(department)
    response = {}
    try:
        if department == "All":
            doctors = UserProfile.objects.filter(is_doctor=True).values(
                "id",
                "profile_pic",
                "first_name",
                "last_name",
                "years_of_experiance",
                "consultation_fee",
                "department",
            )
        else:
            doctors = UserProfile.objects.filter(
                is_doctor=True, department=department
            ).values(
                "id",
                "profile_pic",
                "first_name",
                "last_name",
                "years_of_experiance",
                "consultation_fee",
                "department",
            )

    except UserProfile.DoesNotExist:
        response = {"error": "Doctors not found"}

    response = {"doctors": list(doctors)}
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

            channel.queue_declare(queue="get_doctors", durable=True)

            channel.basic_consume(queue="get_doctors", on_message_callback=on_request)
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
