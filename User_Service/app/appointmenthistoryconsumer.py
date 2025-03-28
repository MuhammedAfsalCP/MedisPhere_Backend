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

logger = logging.getLogger('django')

def on_request(ch, method, properties, body):
    """Handle incoming requests to fetch user data."""
    request_data = json.loads(body)
    id = request_data.get("id")
    
    
    # logger.info(f"Received request for doctor_id: {id}, date: {date}")
    
    response = {}
    # Fetch details for the given doctor and date
    details = DoctorAvailability.objects.select_related('patient').filter(
        doctor__id=id,is_available=False
    ).values(
        'id',
        str('slot'),
        str('date'),
        'is_available',
        'status',
        'patient__first_name',
        'patient__last_name'
    )
    details_list = list(details)
    # Check if any records exist
    cleaned_details = [
        {
            key: list(value)[0] if isinstance(value, set) else value.isoformat() if hasattr(value, 'isoformat') else value
            for key, value in item.items()
        }
        for item in details_list
    ]

    # Check if any records exist
    if not cleaned_details:
        response = {"error": "Details not found"}
    else:
        # Map to frontend-expected structure
        history = [
            {
                "id": item["id"],
                "slot": item["slot"],
                "date": item["date"],
                "status": item["status"],
                "patient_first_name": item["patient__first_name"],
                "patient_last_name": item["patient__last_name"]
            }
            for item in cleaned_details
        ]
        response = {"history": history}
    
    response_body = json.dumps(response)
    logger.info(f"Attempting to send response to reply_to queue: {properties.reply_to}, correlation_id: {properties.correlation_id}")
    
    try:
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            body=response_body,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        )
        logger.info(f"Response sent to reply_to queue: {properties.reply_to}, correlation_id: {properties.correlation_id}")
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
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
            channel = connection.channel()

            channel.queue_declare(queue="appointment_history", durable=True)

            channel.basic_consume(queue="appointment_history", on_message_callback=on_request)
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