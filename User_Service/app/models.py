from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, mobile_number, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, mobile_number=mobile_number, **extra_fields)
        user.set_password(password)

        user.save(using=self._db)
        return user

    def create_superuser(self, email, mobile_number, password=None):
        extra_fields = {
            "is_admin": True,
            "is_staff": True,
            "is_superuser": True,
        }
        user = self.create_user(email, mobile_number, password, **extra_fields)
        user.save(using=self._db)
        return user


class UserProfile(AbstractBaseUser, PermissionsMixin):
    class GenderChoices(models.TextChoices):
        SELECT = "Select"
        Male = "Male"
        Female = "Female"

    class BloodChoices(models.TextChoices):
        SELECT = "Select"
        A_POS = "A+"
        A_NEG = "A-"
        B_POS = "B+"
        B_NEG = "B-"
        AB_POS = "AB+"
        AB_NEG = "AB-"
        O_POS = "O+"
        O_NEG = "O-"

    class DepartmentChoices(models.TextChoices):
        SELECT = "Select", "Select"
        CARDIOLOGY = "Cardiology", "Cardiology"
        NEUROLOGY = "Neurology", "Neurology"
        ORTHOPEDICS = "Orthopedics", "Orthopedics"
        PEDIATRICS = "Pediatrics", "Pediatrics"
        ONCOLOGY = "Oncology", "Oncology"
        DERMATOLOGY = "Dermatology", "Dermatology"
        GYNECOLOGY = "Gynecology", "Gynecology"
        ENT = "ENT", "ENT"

    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=10, unique=True)
    profile_pic = models.ImageField(upload_to="profilepic", null=True, blank=True)
    medical_report = models.ImageField(
        upload_to="medicalreport", null=True, blank=True, default=None
    )
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=6, choices=GenderChoices.choices, default=GenderChoices.SELECT
    )
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Height in centimeters",
        null=True,
        blank=True,
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Weight in kilograms",
        null=True,
        blank=True,
    )
    blood_group = models.CharField(
        max_length=6, choices=BloodChoices.choices, default=BloodChoices.SELECT
    )
    department = models.CharField(
        max_length=20,
        choices=DepartmentChoices.choices,
        help_text="Select the doctor's department",
        null=True,
        blank=True,
    )
    years_of_experiance = models.PositiveIntegerField(
        null=True, blank=True, default=None
    )
    license_number = models.CharField(
        max_length=20, null=True, blank=True, default=None
    )
    license_photo = models.ImageField(
        upload_to="licensephoto", null=True, blank=True, default=None
    )
    consultation_fee = models.IntegerField(null=True, blank=True, default=None)
    upi_id = models.CharField(max_length=20, null=True, blank=True, default=None)

    is_active = models.BooleanField(default=True)
    is_doctor = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["mobile_number"]

    def __str__(self):
        return self.email
