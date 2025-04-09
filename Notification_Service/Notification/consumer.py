import os
import pika
import json
import logging
import time
import django
from datetime import datetime
from django.utils import timezone
import sys
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Notification_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()


from Notification.notification import create_booking_notification

def callback(ch, method, properties, body):
    try:
        message = json.loads(body.decode())
        # doctor_email = message.get('doctor_email')
        patient_email = message.get('patient_email')
        patient_id = message.get('patient_id')
        date_str = message.get('date')  # e.g., "2025-04-09" (string)
        slot = message.get('slot')      # e.g., "09:00 am - 10:00 am" (string)
        doctor_name = message.get('doctor_name')

        if not all([ patient_email, date_str, slot, doctor_name]):
            raise ValueError("Missing required fields in message")

        # Extract the start time from the slot (e.g., "09:00 am" from "09:00 am - 10:00 am")
        slot_start = slot.split(" - ")[0].strip()  # Get "09:00 am"
        
        # Combine date_str (string) and slot_start into a timezone-aware datetime
        try:
            naive_booking_time = datetime.strptime(f"{date_str} {slot_start}", '%Y-%m-%d %I:%M %p')
            booking_time = timezone.make_aware(naive_booking_time)
        except ValueError as e:
            raise ValueError(f"Invalid slot format: {slot}. Expected format like '09:00 am - 10:00 am'") from e

        logger.info(f"Received message: patient_email={patient_email}, date={date_str}, slot={slot}")

        # Call create_booking_notification
        create_booking_notification(
            
            patient_id=patient_id,  # Adjust if you have actual IDs
            booking_time=booking_time,  # Timezone-aware datetime
            slot=slot,  # Full slot string for display
            patient_email=patient_email,
            doctor_name=doctor_name
        )

        if properties.reply_to and properties.correlation_id:
            response = {
                "status": "processed",
                "message": f"Notification scheduled for appointment with Dr. {doctor_name} on {date_str} in slot {slot}"
            }
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                body=json.dumps(response).encode(),
                properties=pika.BasicProperties(correlation_id=properties.correlation_id)
            )
            logger.info(f"Response sent to {properties.reply_to} with correlation_id {properties.correlation_id}")
        else:
            logger.info("No reply_to queue specified, skipping response")

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except ValueError as e:
        logger.error(f"Message validation failed: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def start_consumer():
    retry_delay = 5
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            channel = connection.channel()
            channel.queue_declare(queue='booking_notifications', durable=True)
            channel.basic_consume(queue='booking_notifications', on_message_callback=callback)
            logger.info("Starting consumer... Press CTRL+C to stop.")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection failed, retrying in {retry_delay} seconds: {str(e)}")
            time.sleep(retry_delay)
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            if 'channel' in locals():
                channel.stop_consuming()
            if 'connection' in locals():
                connection.close()
            break
        except Exception as e:
            logger.error(f"Unexpected error, retrying in {retry_delay} seconds: {str(e)}")
            time.sleep(retry_delay)
        finally:
            if 'connection' in locals() and not connection.is_closed:
                connection.close()

if __name__ == "__main__":
    start_consumer()