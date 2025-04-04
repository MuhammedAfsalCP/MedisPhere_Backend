import json
import pika
import django
import os
import sys
from django.conf import settings
import logging
import time
from django.db.models import Q
from django.db.models import Count
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Import your models
from app.models import DoctorAvailability, UserProfile,TimeSlotChoices

logger = logging.getLogger("django")


def on_request(ch, method, properties, body):
    """Handle incoming requests to fetch user data."""
    request_data = json.loads(body)
    id = request_data.get("id")
    logger.info(id)
    # logger.info(f"Received request for doctor_id: {id}, date: {date}")
    today = datetime.now().date()  # Current date
    one_month_ago = today - relativedelta(months=1)
    response = {}
    # Fetch details for the given doctor and date
    Booking_data = (
        DoctorAvailability.objects
        .filter(Q(doctor__id=id)&Q(date__range=[one_month_ago, today]))  # Filter for the specific doctor
        .aggregate(
            morning_bookings=Count(
                'id',
                filter=Q(slot__in=[
                    TimeSlotChoices.NINE_TEN_AM,
                    TimeSlotChoices.TEN_ELEVEN_AM,
                    TimeSlotChoices.ELEVEN_TWELVE_AM
                ]) & Q(status='Completed')
            ),
            afternoon_bookings=Count(
                'id',
                filter=Q(slot__in=[
                    TimeSlotChoices.TWELVE_ONE_PM,
                    TimeSlotChoices.ONE_TWO_PM,
                    TimeSlotChoices.TWO_THREE_PM,
                    TimeSlotChoices.THREE_FOUR_PM,
                    TimeSlotChoices.FOUR_FIVE_PM
                ]) & Q(status='Completed')
            ),
            evening_bookings=Count(
                'id',
                filter=Q(slot__in=[
                    TimeSlotChoices.FIVE_SIX_PM,
                    TimeSlotChoices.SIX_SEVEN_PM,
                    TimeSlotChoices.SEVEN_EIGHT_PM,
                    TimeSlotChoices.EIGHT_NINE_PM
                ]) & Q(status='Completed')
            )
        )
    )

    # Ensure a default response if no data exists
    response = {
        "Booking_Times": Booking_data 
    }
    
    # Check if any records exist

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

            channel.queue_declare(queue="dashboard_booking", durable=True)

            channel.basic_consume(
                queue="dashboard_booking", on_message_callback=on_request
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
