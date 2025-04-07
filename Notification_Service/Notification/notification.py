# notification_service/notification.py (snippet)
from .models import Notification
from .tasks import send_notification_email
import json
from datetime import timedelta
def create_booking_notification(doctor_id, patient_id, booking_time, slot, patient_email, doctor_name):
    scheduled_time = booking_time - timedelta(days=1)  # 1 day before booking
    message = {
        'text': f"Dear Patient,\n\nThis is a reminder for your appointment with Dr. {doctor_name} on {booking_time.strftime('%Y-%m-%d')} at {slot}. Please arrive on time.\n\nRegards,\nClinic Team",
        'patient_email': patient_email,
        'doctor_id': doctor_id,
        'slot': slot
    }
    notification = Notification.objects.create(
        user_id=patient_id,
        message=json.dumps(message),
        scheduled_at=scheduled_time
    )
    send_notification_email.apply_async(
        args=[notification.id],
        eta=scheduled_time
    )