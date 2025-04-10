
import os
from celery import Celery

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Notification_Service.settings')

# Initialize Celery
celery = Celery(
    'Notification_Service',
    broker='amqp://guest:guest@rabbitmq:5672//',
    backend='redis://redis:6379/0',
    include=['Notification.tasks']  # Resolves to /app/Notification/tasks.py
)

# Load Celery config from Django settings
celery.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks
celery.autodiscover_tasks()

# Configure queue settings
celery.conf.task_default_queue = 'notification_queue'
celery.conf.task_queues = {
    'notification_queue': {
        'binding_key': 'notification_queue'
    }
}
celery.conf.task_default_routing_key = 'notification_queue'

# Set timezone and debugging options
celery.conf.timezone = 'UTC'
celery.conf.task_track_started = True
celery.conf.result_expires = 3600