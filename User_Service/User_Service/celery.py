# # User_Service/celery.py
# import os
# from celery import Celery

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")

# app = Celery(
#     "User_Service",
#     broker="redis://redis:6379/0",  # Match logs
#     backend="redis://redis:6379/0"
# )

# app.config_from_object("django.conf:settings", namespace="CELERY")
# app.autodiscover_tasks(["app"])

# User_Service/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'User_Service.settings')

app = Celery(
    'User_Service',
    broker='amqp://guest:guest@rabbitmq:5672//',
    backend='redis://redis:6379/0',
    include=['app.tasks']
)

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_default_queue = 'user_queue'
app.conf.task_queues = {
    'user_queue': {'binding_key': 'user_queue'},
}
app.conf.task_default_routing_key = 'user_queue'

if __name__ == '__main__':
    app.start()