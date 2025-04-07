# notification_service/models.py
from django.db import models

class Notification(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )

    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField()  # Stores UserProfile ID from user_service
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'

    def __str__(self):
        return f"Notification for user_id {self.user_id}: {self.message[:50]}"