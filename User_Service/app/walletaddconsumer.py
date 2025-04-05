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
from decimal import Decimal
# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Import your models
from app.models import DoctorAvailability, UserProfile

logger = logging.getLogger("django")
from app.tasks import send_appointment_email


def on_request(ch, method, properties, body):
    """Process a wallet update request from RabbitMQ."""
    request_data = json.loads(body)
    room_id = request_data.get("room_id")
    amount = request_data.get("amount")
    response = {}

    # Validate inputs
    if not room_id:
        response = {"error": "room_id is required"}
        logger.error(f"Missing room_id")
    elif not isinstance(amount, str) or not amount.strip():  # Check if amount is a non-empty string
        response = {"error": "Amount must be a non-empty string"}
        logger.error(f"Invalid input: amount={amount}")
    else:
        try:
            # Fetch room and update wallet atomically
            amount_decimal = Decimal(amount)
            with transaction.atomic():
                room = DoctorAvailability.objects.select_related("doctor").get(id=room_id)
                wallet = Decimal(str(room.doctor.wallet))
                room.room_created = False
                room.status = "Completed"
                room.doctor.wallet = wallet + amount_decimal
                room.doctor.save()
                room.save()
                # logger.info(f"Wallet updated for doctor {room.doctor.id}: {wallet} -> {wallet + amount}")
            response = {"message": "wallet added"}
        except DoctorAvailability.DoesNotExist:
            response = {"error": "Room not found for the given ID"}
            logger.error(f"Room not found: room_id={room_id}")
        except Exception as e:
            response = {"error": f"Internal error: {str(e)}"}
            logger.error(f"Error processing request: {str(e)}")

    # Send response back to the requester
    try:
        logger.info(f"Sending response to {properties.reply_to} with correlation_id {properties.correlation_id}")
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            body=json.dumps(response),
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        )
        logger.info(f"Response sent: {response}")
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

            channel.queue_declare(queue="walletadd", durable=True)

            channel.basic_consume(queue="walletadd", on_message_callback=on_request)
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
