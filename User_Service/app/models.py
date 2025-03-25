from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
import uuid

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


class TimeSlotChoices(models.TextChoices):

    NINE_TEN_AM = "09:00 am - 10:00 am","09:00 am - 10:00 am"
    TEN_ELEVEN_AM = "10:00 am - 11:00 am","10:00 am - 11:00 am"
    ELEVEN_TWELVE_AM = "11:00 am - 12:00 pm","11:00 am - 12:00 pm"
    TWELVE_ONE_PM = "12:00 pm - 1:00 pm","12:00 pm - 1:00 pm"
    ONE_TWO_PM = "1:00 pm - 2:00 pm","1:00 pm - 2:00 pm"
    TWO_THREE_PM = "2:00 pm - 3:00 pm","2:00 pm - 3:00 pm"
    THREE_FOUR_PM = "3:00 pm - 4:00 pm","3:00 pm - 4:00 pm"
    FOUR_FIVE_PM = "4:00 pm - 5:00 pm","4:00 pm - 5:00 pm"
    FIVE_SIX_PM = "5:00 pm - 6:00 pm","5:00 pm - 6:00 pm"
    SIX_SEVEN_PM = "6:00 pm - 7:00 pm","6:00 pm - 7:00 pm"
    SEVEN_EIGHT_PM ="7:00 pm - 8:00 pm","7:00 pm - 8:00 pm"
    EIGHT_NINE_PM = "8:00 pm - 9:00 pm","8:00 pm - 9:00 pm"

class StatusChoices(models.TextChoices):

    PENDING = "Pending"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"



class DoctorAvailability(models.Model):
    doctor = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        limit_choices_to={"is_doctor": True},
        related_name="availabilities",
    )
    date = models.DateField(help_text="Date of availability")
    slot = models.CharField(
        max_length=19,
        choices=TimeSlotChoices.choices,
        help_text="Select the available time slot (each slot is one hour)",
    )
    is_available = models.BooleanField(
        default=True, help_text="Indicates if the doctor is available during this slot"
    )
    patient = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        limit_choices_to={"is_doctor": False},
    )
    meet_link=models.CharField(max_length=500,blank=True,null=True)
    room_created = models.BooleanField(
        default=False
    )
    status = models.CharField(
        max_length=9,
        choices=StatusChoices.choices,
        blank=True,
        null=True
    )
    amount=models.CharField(max_length=20,blank=True,null=True,default=None)
    isDelete=models.BooleanField(default=False)
    
    class Meta:
        
        ordering = ["date", "slot"]

    def __str__(self):
        slot_label = dict(TimeSlotChoices.choices).get(self.slot, self.slot)
        return f"{self.doctor.first_name} {self.doctor.last_name} on {self.date} at {slot_label}"
