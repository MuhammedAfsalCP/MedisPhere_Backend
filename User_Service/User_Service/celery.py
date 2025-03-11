# User_Service/celery.py
from celery import Celery

app = Celery(
    "User_Service", broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)

# Auto-discover tasks in all installed apps
app.autodiscover_tasks(["app"])  # Add this line

# Import tasks explicitly (alternative to autodiscover)
from app.tasks import send_appointment_email  # Add this line
