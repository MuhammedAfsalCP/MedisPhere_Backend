from django.db import models

# Create your models here.
class Prescription(models.Model):
    doctor_id=models.IntegerField()
    doctor_name=models.CharField(max_length=30)
    doctor_department=models.CharField(max_length=30)
    patient_id=models.IntegerField()
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    prescription_id=models.IntegerField()
