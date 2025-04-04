

import pika
import json
import time
import logging
import os
import django
import sys
from django.db import transaction
from urllib.parse import unquote

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Import your models
from app.models import DoctorAvailability, UserProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("consumer.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
logger.info("Hello from RabbitMQ consumer")

def connect_to_rabbitmq():
    """Retries RabbitMQ connection until successful"""
    retries = 15
    for i in range(retries):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
            )
            logger.info("Connected to RabbitMQ successfully.")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"Retry {i+1}/{retries} - Waiting for RabbitMQ...")
            time.sleep(5)
    logger.error("Failed to connect to RabbitMQ after multiple retries.")
    raise Exception("Failed to connect to RabbitMQ after multiple retries.")

def roomupdate(data):
    """Update or create the room status in DoctorAvailability for the doctor"""
    room_name = data.get("room_name")
    email = unquote(data.get("email") or "")  # Decode email
    date = data.get("date")
    slot = unquote(data.get("slot") or "")    # Decode slot
    logger.info(email)
    if not room_name:
        logger.error("No room_name provided in the message.")
        return {"error": "Room name is required"}
    if not email or not date or not slot:
        logger.error("Missing email, date, or slot in the message.")
        return {"error": "Email, date, and slot are required"}

    # Construct the meet_link with decoded email
    meet_link = room_name
    logger.info(f"Constructed meet_link: {meet_link}")  # Fixed logging

    try:
        patient=UserProfile.objects.get(email=email, is_doctor=False)
        with transaction.atomic():
            # Check for existing room by room_name
            existing_room = DoctorAvailability.objects.filter(patient=patient,slot=slot,date=date).first()
            if existing_room:
                existing_room.meet_link = meet_link
                existing_room.room_created = True
                
                existing_room.save()
                logger.info(f"Updated existing room {room_name} for doctor with email {email}")
            else:
                # Create a new room
               
                logger.info("slot not booked")

            return {
                "room_created": True,
                "meet_link": meet_link,
                "email": email,
                "date": date,
                "slot": slot,
            }

    except Exception as e:
        logger.error(f"Database error while processing room {room_name}: {e}")
        return {"error": e}

def callback(ch, method, properties, body):
    """Handles incoming RabbitMQ messages"""
    try:
        data = json.loads(body)
        logger.info(f"Received message: {data}")
        response = roomupdate(data)
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in received message.")
        response = {"error": "Invalid JSON format"}
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        response = {"error": str(e)}

    ch.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        body=json.dumps(response),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)
    logger.info(f"Sent response: {response}")

def start_consumer():
    """Starts RabbitMQ consumer with reconnection logic"""
    while True:
        try:
            logger.info("Connecting to RabbitMQ...")
            connection = connect_to_rabbitmq()
            channel = connection.channel()
            channel.queue_declare(queue="roomupdate")
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue="roomupdate",
                on_message_callback=callback
            )
            logger.info(" [✔] Waiting for messages on 'roomupdate' queue...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection lost: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Consumer error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    logger.info("Starting consumer... Waiting 5 seconds to ensure RabbitMQ is ready.")
    time.sleep(5)
    start_consumer()