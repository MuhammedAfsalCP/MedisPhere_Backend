
from rest_framework import serializers
from .models import Prescription

class PrescriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ['doctor_id', 'patient_id', 'notes','prescription_id','doctor_name','doctor_department']
class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ['id', 'doctor_id', 'patient_id', 'notes', 'prescription_id']

class PrescriptionsShowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ['prescription_id','doctor_name','created_at','doctor_department','notes']