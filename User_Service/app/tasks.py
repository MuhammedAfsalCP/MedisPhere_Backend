from celery import shared_task
from django.core.mail import EmailMessage
import os
from dotenv import load_dotenv
import pika
import json
import logging
import uuid
# Load environment variables
load_dotenv()

# Get the Celery app instance (assuming it's defined in User_Service/celery.py)
from User_Service.celery import app as celery_app

# Set up logging
logger = logging.getLogger(__name__)

@celery_app.task(queue='user_queue')
def send_appointment_email(to_email, subject, message):
    """
    Send email asynchronously using Celery.
    """
    from_email = os.getenv("EMAIL_HOST_USER")
    try:
        email = EmailMessage(subject, message, from_email, [to_email])
        email.send()
        logger.info(f"Email sent to {to_email}")
        return f"Email sent to {to_email}"
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise
@celery_app.task(queue='user_queue', autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def publish_booking_event(patient_id, patient_email, date, slot, doctor_name):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()
        channel.queue_declare(queue='booking_notifications', durable=True)

        # Declare a temporary reply queue
        reply_queue = channel.queue_declare(queue='', exclusive=True).method.queue
        correlation_id = str(uuid.uuid4())  # Add import uuid at the top

        message = {
            
            'patient_email': patient_email,
            'date': date,
            'slot': slot,
            'patient_id':patient_id,
            'doctor_name': doctor_name
        }

        channel.basic_publish(
            exchange='',
            routing_key='booking_notifications',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                reply_to=reply_queue,
                correlation_id=correlation_id
            )
        )

        # Optional: Wait for response (blocking, use with caution in Celery)
        def on_response(ch, method, props, body):
            if props.correlation_id == correlation_id:
                logger.info(f"Received response: {body.decode()}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                ch.stop_consuming()

        channel.basic_consume(queue=reply_queue, on_message_callback=on_response)
        channel.start_consuming()  # Blocks until response is received

        logger.info(f"Booking event published: {message}")
    except Exception as e:
        logger.error(f"Failed to publish booking event: {str(e)}")
        raise
    finally:
        if 'connection' in locals() and not connection.is_closed:
            connection.close()