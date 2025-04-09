from django.utils import timezone
from datetime import timedelta
import json
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from .models import Notification
from .tasks import send_notification_email


def create_booking_notification(doctor_id, patient_id, booking_time, slot, patient_email, doctor_name):
    """
    Create a booking notification and schedule it to be sent 1 day before the appointment.

    Args:
        doctor_id (int): ID of the doctor.
        patient_id (int): ID of the patient (user_id in Notification model).
        booking_time (datetime): Date and time of the booking.
        slot (str): Time slot of the appointment (e.g., "10:00 AM").
        patient_email (str): Email address of the patient.
        doctor_name (str): Name of the doctor.
    """
    try:
        # Calculate scheduled time (1 day before booking)
        scheduled_time = booking_time - timedelta(days=1)
        
        # Ensure scheduled_time is in the future; if not, adjust logic as needed
        if scheduled_time < timezone.now():
            scheduled_time = timezone.now() + timedelta(minutes=5)  # Fallback to 5 minutes from now

        # Create the notification message as JSON
        message = {
            'text': (
                f"Dear Patient,\n\n"
                f"This is a reminder for your appointment with Dr. {doctor_name} "
                f"on {booking_time.strftime('%Y-%m-%d')} at {slot}. "
                f"Please arrive on time.\n\n"
                f"Regards,\nClinic Team"
            ),
            'patient_email': patient_email,
            'doctor_id': doctor_id,
            'slot': slot
        }

        # Create the Notification instance
        notification = Notification.objects.create(
            user_id=patient_id,
            message=json.dumps(message),
            scheduled_at=scheduled_time,
            status='pending'  # Explicitly set for clarity, though default is 'pending'
        )

        # Create or get a CrontabSchedule for the exact time
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=scheduled_time.minute,
            hour=scheduled_time.hour,
            day_of_month=scheduled_time.day,
            month_of_year=scheduled_time.month,
            year=scheduled_time.year,
        )

        # Create a unique PeriodicTask for this notification
        task_name = f"send-notification-{notification.id}-{timezone.now().timestamp()}"  # Unique name
        PeriodicTask.objects.create(
            crontab=schedule,
            name=task_name,
            task='notification_service.tasks.send_notification_email',  # Full task path
            args=json.dumps([notification.id]),
            one_off=True,  # Run once and expire
            start_time=scheduled_time,
            expires=scheduled_time + timedelta(hours=1)  # Expire 1 hour after scheduled time
        )

        print(f"Notification {notification.id} scheduled for {scheduled_time}")

    except Exception as e:
        # Log the error (in a real system, use a proper logging framework)
        print(f"Error creating notification: {str(e)}")
        # Optionally, raise the exception to be handled by the caller (e.g., consumer.py)
        raise