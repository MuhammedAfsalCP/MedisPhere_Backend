from django.urls import path
from .views import BookingAppointmentAPIView, DoctorSlotCreating
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path(
        "book_appointment/",
        BookingAppointmentAPIView.as_view(),
        name="booking_appointment",
    ),
    path(
        "doctor_slot_creating/",
        DoctorSlotCreating.as_view(),
        name="doctor_slot_creating",
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)