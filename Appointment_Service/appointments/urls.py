from django.urls import path
from .views import CreateAppointmentAPIView

urlpatterns = [
    path('api/create_appointment/', CreateAppointmentAPIView.as_view(), name='create_appointment'),
]
