from celery import shared_task
from django.core.mail import EmailMessage
import os
from dotenv import load_dotenv
import pika
from datetime import datetime
import json
load_dotenv()


@shared_task
def send_appointment_email(to_email, subject, message):
    from_email = os.getenv("EMAIL_HOST_USER")
    """Send email asynchronously using Celery"""
    email = EmailMessage(
        subject, message, from_email, [to_email]  # Sender email  # Recipient email
    )
    email.send()
    return f"Email sent to {to_email}"


@shared_task
def publish_booking_event(doctor_id, patient_id, date, slot, patient_email, doctor_name):
    """Publish booking event to RabbitMQ for NotificationService to process"""
    # RabbitMQ connection
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='booking_notifications', durable=True)

    # Parse slot start time (e.g., "09:00 am - 10:00 am" -> "09:00")
    slot_start = slot.split(" - ")[0].strip()
    booking_time = datetime.strptime(f"{date} {slot_start}", "%Y-%m-%d %I:%M %p")

    # Message payload
    message = {
        'doctor_id': doctor_id,
        'patient_id': patient_id,
        'booking_time': booking_time.strftime('%Y-%m-%d %H:%M:%S'),
        'patient_email': patient_email,
        'slot': slot,
        'doctor_name': f"{doctor_name}"  # Include doctor's full name
    }
    channel.basic_publish(
        exchange='',
        routing_key='booking_notifications',
        body=json.dumps(message).encode(),
        properties=pika.BasicProperties(delivery_mode=2)  # Persistent message
    )
    connection.close()
    print(f"Published booking event: {message}")
    return f"Booking event published for patient {patient_id}"