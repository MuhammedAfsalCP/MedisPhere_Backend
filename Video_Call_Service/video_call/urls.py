# vide
from django.urls import path
from .views import WalletEditing

urlpatterns = [
    path('wallet_editing/', WalletEditing.as_view(), name='wallet_editing'),
    # path('doctor_slot_creating/', DoctorSlotCreating.as_view(), name='doctor_slot_creating'),
]
