import json
import pika
import django
import os
import sys
from django.conf import settings

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Import models
from app.models import UserProfile  

def on_request(ch, method, properties, body):
    """Handle incoming requests to fetch user data."""
    request_data = json.loads(body)
    user_id = request_data.get("user_id")

    response = {}

    try:
        user = UserProfile.objects.get(id=user_id)
        response = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_doctor": user.is_doctor,
            "is_admin": user.is_admin,
            "is_staff": user.is_staff,
        }
    except UserProfile.DoesNotExist:
        response = {"error": "User not found"}

    response_body = json.dumps(response)

    # Send response back using the reply_to queue
    ch.basic_publish(
        exchange="",
        routing_key=properties.reply_to,  # Dynamic response queue
        body=response_body,
        properties=pika.BasicProperties(correlation_id=properties.correlation_id),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_user_service():
    """Start RabbitMQ consumer for user service."""
    rabbitmq_host = getattr(settings, "RABBITMQ_HOST", "rabbitmq")  # Use settings

    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
            channel = connection.channel()

            # Declare request queue
            channel.queue_declare(queue="get_user", durable=True)

            # Start consuming messages
            channel.basic_consume(queue="get_user", on_message_callback=on_request)

            print(" [x] Waiting for user requests...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            print(" [!] RabbitMQ not available, retrying in 5 seconds...")
            import time
            time.sleep(5)

if __name__ == "__main__":
    start_user_service()
