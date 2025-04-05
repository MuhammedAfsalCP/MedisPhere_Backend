# app/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, DoctorAvailability


class UserProfileAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "mobile_number",
        "first_name",
        "last_name",
        "is_staff",
        "is_doctor",
        "wallet"
    )

    # Fields displayed when viewing/changing an existing user.
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal Info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "mobile_number",
                    "profile_pic",
                    "medical_report",
                    "date_of_birth",
                    "gender",
                    "height",
                    "weight",
                    "blood_group",
                    "department",
                    "years_of_experiance",
                )
            },
        ),
        (
            _("License Information"),
            {
                "fields": (
                    "license_number",
                    "license_photo",
                    "consultation_fee",
                    "upi_id",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_admin",
                    "is_doctor",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important Dates"), {"fields": ("last_login",)}),
    )

    # Fields displayed when creating a new user.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "mobile_number",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    search_fields = ("email", "first_name", "last_name", "mobile_number")


admin.site.register(UserProfile, UserProfileAdmin)


class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("doctor", "date", "slot", "is_available", "patient", "room_created","status")
    list_filter = ("date", "is_available")
    search_fields = ("doctor__email",)
    ordering = ("date", "slot")


admin.site.register(DoctorAvailability, DoctorAvailabilityAdmin)
