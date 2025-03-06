from celery import shared_task
from django.core.mail import EmailMessage
import os
from dotenv import load_dotenv
load_dotenv()

@shared_task
def send_appointment_email(to_email, subject, message):
    from_email = os.getenv("EMAIL_HOST_USER")
    """Send email asynchronously using Celery"""
    email=EmailMessage(
        subject,
        message,
        from_email,  # Sender email
        [to_email]  # Recipient email
        
    )
    email.send()
    return f"Email sent to {to_email}"
