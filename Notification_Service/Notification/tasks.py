# Notification_Service/Notification/tasks.py
from celery import shared_task
from django.core.mail import EmailMessage
from django.utils import timezone
from .models import Notification
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

@shared_task(queue='notification_queue')
def send_notification_email(notification_id):
    # Existing implementation (as provided earlier)
    notification = Notification.objects.get(id=notification_id)
    if notification.scheduled_at and notification.scheduled_at > timezone.now():
        logger.info(f"Notification {notification_id} scheduled for future: {notification.scheduled_at}")
        return
    message_data = notification.get_message_data()
    patient_email = message_data.get('patient_email')
    message_text = message_data.get('text')
    if not patient_email or not message_text:
        raise ValueError("Missing patient_email or message_text")
    email = EmailMessage(
        subject="Appointment Reminder",
        body=message_text,
        from_email=os.getenv("EMAIL_HOST_USER"),
        to=[patient_email]
    )
    email.send()
    notification.status = 'sent'
    notification.sent_at = timezone.now()
    notification.save()
    logger.info(f"Email sent for notification {notification_id} to {patient_email}")

@shared_task(queue='notification_queue')
def check_pending_notifications():
    """Check for pending notifications and schedule email tasks."""
    pending_notifications = Notification.objects.filter(status='pending', scheduled_at__lte=timezone.now())
    for notification in pending_notifications:
        send_notification_email.delay(notification.id)
        logger.info(f"Scheduled email for pending notification {notification.id}")