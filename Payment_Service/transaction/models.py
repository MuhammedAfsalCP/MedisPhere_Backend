from django.db import models

# Create your models here.
class StatusChoices(models.TextChoices):

    PENDING = "Pending"
    COMPLETED = "Completed"
    REJECTED = "Rejected"

class Transactions(models.Model):
    doctor=models.IntegerField()
    amount=models.DecimalField(
        max_digits=10,  
        decimal_places=2, 
    )
    status = models.CharField(
        max_length=9, choices=StatusChoices.choices, blank=True, null=True
    )
    date = models.DateField(auto_now_add=True)
    transaction_id=models.CharField(max_length=20,null=True,blank=True)