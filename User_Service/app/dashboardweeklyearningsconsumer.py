import json
import pika
import django
import os
import sys
from django.conf import settings
import logging
import time
from django.db.models import Q
from django.db.models import Count,Sum
from datetime import datetime, timedelta
from decimal import Decimal

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Import your models
from app.models import DoctorAvailability, UserProfile,TimeSlotChoices

logger = logging.getLogger("django")


def on_request(ch, method, properties, body):
    """Handle incoming requests to fetch weekly earnings for a doctor."""
    try:
        request_data = json.loads(body)
        doctor_id = request_data.get("id")  # Renamed 'id' to 'doctor_id' for clarity
        logger.info(f"Received request for doctor_id: {doctor_id}")

        # Calculate date range (last 12 days)
        end_date = datetime.now().date() - timedelta(days=1)  # Yesterday (April 4, 2025)
        start_date = end_date - timedelta(days=9)  # 12 days ago (March 25, 2025)
        logger.info(f"Querying earnings from {start_date} to {end_date}")

        # Query revenue for the last 12 days
        weekly_earnings = DoctorAvailability.objects.filter(
            Q(date__range=(start_date, end_date)) &
            Q(status="Completed") &
            Q(doctor__id=doctor_id)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Ensure weekly_earnings is a Decimal
        weekly_earnings = Decimal(str(weekly_earnings)) if weekly_earnings else Decimal('0')

        # Prepare response
        response = {
            "Weekly Earnings": str(weekly_earnings)  # Convert to string for JSON serialization
        }
        logger.info(f"Calculated weekly earnings for doctor {doctor_id}: {weekly_earnings}")

        # Serialize response
        response_body = json.dumps(response)
        logger.info(
            f"Attempting to send response to reply_to queue: {properties.reply_to}, "
            f"correlation_id: {properties.correlation_id}"
        )

        # Send response
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            body=response_body,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        )
        logger.info(
            f"Response sent to reply_to queue: {properties.reply_to}, "
            f"correlation_id: {properties.correlation_id}"
        )

    except json.JSONDecodeError as e:
        response = {"error": "Invalid request data"}
        logger.error(f"Failed to decode request body: {str(e)}")
        response_body = json.dumps(response)
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            body=response_body,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        )
    except DoctorAvailability.DoesNotExist:
        response = {"error": "No records found for the given doctor"}
        logger.error(f"No records found for doctor_id: {doctor_id}")
        response_body = json.dumps(response)
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            body=response_body,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        )
    except Exception as e:
        response = {"error": f"Internal error: {str(e)}"}
        logger.error(f"Error processing request for doctor_id {doctor_id}: {str(e)}")
        response_body = json.dumps(response)
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            body=response_body,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        )

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

            channel.queue_declare(queue="dashboard_weekily_earnings", durable=True)

            channel.basic_consume(
                queue="dashboard_weekily_earnings", on_message_callback=on_request
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
