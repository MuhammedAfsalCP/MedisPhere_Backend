from django.urls import path
from .patientviews import (
    BookingAppointmentAPIView,
    DoctorFetching,
    Specificdoctorfetching,
    Slotfetching,
    AppointmentBookingViewMore,
    Reschedulig,
    Canceling,
)
from .doctorviews import (
    DoctorCall,
    DoctorSlotCreating,
    SlotDeleting,
    AppointmentHistory,
    AppointmentHistoryViewMore,
    AllHistory,
    BookigTimes
)
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
    path(
        "appointment_booking_viewmore/<int:id>/",
        AppointmentBookingViewMore.as_view(),
        name="slot_fetching",
    ),
    path(
        "rescheduling/",
        Reschedulig.as_view(),
        name="rescheduling",
    ),
    path(
        "canceling/",
        Canceling.as_view(),
        name="canceling",
    ),
    path(
        "slotdeleting/",
        SlotDeleting.as_view(),
        name="slotdeleting",
    ),
    path(
        "appointmenthistory/",
        AppointmentHistory.as_view(),
        name="appointmenthistory",
    ),
    path(
        "appointmenthistoryviewmore/<int:id>/",
        AppointmentHistoryViewMore.as_view(),
        name="appointmenthistoryviewmore",
    ),
    path(
        "doctorcall/<int:id>/",
        DoctorCall.as_view(),
        name="doctorcall",
    ),
    path(
        "allhistory/",
        AllHistory.as_view(),
        name="allhistory",
    ),
    path(
        "bookingtimes/",
        BookigTimes.as_view(),
        name="bookingtimes",
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
