
from django.utils import timezone
from datetime import timedelta
import json
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from .models import Notification
from .tasks import send_notification_email
import logging

logger = logging.getLogger(__name__)

def create_booking_notification(patient_id, booking_time, slot, patient_email, doctor_name):
    try:
        if not timezone.is_aware(booking_time):
            booking_time = timezone.make_aware(booking_time)
        logger.info(f"Booking time received: {booking_time}")

        scheduled_time = booking_time - timedelta(days=1)
        now = timezone.now()
        logger.info(f"Initial scheduled time: {scheduled_time}, now: {now}")

        if scheduled_time < now:
            scheduled_time = now + timedelta(minutes=5)
            logger.info(f"Adjusted scheduled time to: {scheduled_time}")

        message = {
            'text': (
                f"Dear Patient,\n\n"
                f"This is a reminder for your appointment with Dr. {doctor_name} "
                f"on {booking_time.strftime('%Y-%m-%d')} at {slot}. "
                f"Please arrive on time.\n\n"
                f"Regards,\nClinic Team"
            ),
            'patient_email': patient_email,
            'doctor_name': doctor_name,
            'slot': slot
        }

        notification = Notification.objects.create(
            user_id=patient_id,
            message=json.dumps(message),
            scheduled_at=scheduled_time,
            status='pending'
        )
        logger.info(f"Notification created: id={notification.id}")

        schedule, created = CrontabSchedule.objects.get_or_create(
            minute=scheduled_time.minute,
            hour=scheduled_time.hour,
            day_of_month=scheduled_time.day,
            month_of_year=scheduled_time.month
        )
        logger.info(f"CrontabSchedule {'created' if created else 'retrieved'}: id={schedule.id}")

        task_name = f"send-notification-{notification.id}-{timezone.now().timestamp()}"
        task = PeriodicTask.objects.create(
            crontab=schedule,
            name=task_name,
            task='Notification.tasks.send_notification_email',
            args=json.dumps([notification.id]),
            one_off=True,
            start_time=scheduled_time,
            expires=scheduled_time + timedelta(hours=1)
        )
        logger.info(f"PeriodicTask created: name={task_name}, id={task.id}, start_time={scheduled_time}")

    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}", exc_info=True)
        raise