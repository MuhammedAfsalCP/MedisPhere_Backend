# Notification_Service/notification/models.py
from django.db import models
import json
class Notification(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )

    # id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(help_text="ID of the UserProfile from user_service")
    message = models.TextField(help_text="JSON string containing patient_email and text")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text="Scheduled time for sending the notification")
    sent_at = models.DateTimeField(null=True, blank=True)
    test_field = models.CharField(max_length=10, default='test')  # Temporary dummy field

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for user_id {self.user_id}: {self.message[:50]}"

    def get_message_data(self):
        try:
            return json.loads(self.message)
        except json.JSONDecodeError:
            return {}