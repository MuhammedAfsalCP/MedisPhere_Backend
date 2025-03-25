from django.urls import path
from .views import BookingAppointmentAPIView, DoctorSlotCreating,DoctorFetching,Specificdoctorfetching,Slotfetching
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
    path(
        "doctors_fetching/<str:department>/",
        DoctorFetching.as_view(),
        name="doctors_fetching",
    ),
    path(
        "specific_doctor_fetching/<int:id>/",
        Specificdoctorfetching.as_view(),
        name="specific_doctor_fetching",
    ),
    path(
        "slot_fetching/<int:id>/<str:date>/",
        Slotfetching.as_view(),
        name="slot_fetching",
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)