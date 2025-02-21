from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
# Create your models here.
class user_profile(AbstractBaseUser):
    email=models.EmailField(unique=True)
    mobile_number=models.PositiveIntegerField(max_length=10)