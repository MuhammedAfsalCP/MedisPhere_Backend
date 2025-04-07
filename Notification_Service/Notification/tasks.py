# notification_service/tasks.py
from celery import shared_task
import smtplib
from email.mime.text import MIMEText
from django.utils import timezone
from .models import Notification
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@shared_task
def send_notification_email(notification_id):
    """Send an email notification for a scheduled appointment."""
    notification = None  # initialize here

    try:
        # Fetch the notification
        notification = Notification.objects.get(id=notification_id)

        # Parse the JSON message to extract email and text
        message_data = json.loads(notification.message)
        patient_email = message_data['patient_email']
        message_text = message_data['text']

        # Email configuration from environment variables
        from_email = os.getenv("EMAIL_HOST_USER")
        email_password = os.getenv("EMAIL_HOST_PASSWORD")
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))

        # Prepare email
        subject = "Appointment Reminder"
        msg = MIMEText(message_text)
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = patient_email

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(from_email, email_password)
            server.send_message(msg)

        # Update notification status to 'sent'
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.save()
        print(f"Email sent for notification {notification_id} to {patient_email}")

    except Notification.DoesNotExist:
        print(f"Notification {notification_id} not found")

    except json.JSONDecodeError:
        if notification:
            notification.status = 'failed'
            notification.sent_at = timezone.now()
            notification.save()
        print(f"Failed to parse message for notification {notification_id}")

    except smtplib.SMTPException as e:
        if notification:
            notification.status = 'failed'
            notification.sent_at = timezone.now()
            notification.save()
        print(f"SMTP error sending email for notification {notification_id}: {str(e)}")

    except Exception as e:
        if notification:
            notification.status = 'failed'
            notification.sent_at = timezone.now()
            notification.save()
        print(f"Failed to send email for notification {notification_id}: {str(e)}")
