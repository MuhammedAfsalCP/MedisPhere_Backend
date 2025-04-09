import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Notification_Service.settings')

app = Celery(
    'Notification_Service',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0',
    include=['Notification.tasks']
)

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-pending-notifications': {
        'task': 'Notification.tasks.check_pending_notifications',
        'schedule': 300.0,  # 5 minutes
        'args': (),
    },
}

app.conf.task_default_queue = 'notification_queue'
app.conf.task_queues = {'notification_queue': {'binding_key': 'notification_queue'}}
app.conf.task_default_routing_key = 'notification_queue'

app.conf.timezone = 'UTC'