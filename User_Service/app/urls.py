"""
URL configuration for User_Service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from .views import (
    Register_Validate,
    Register_User,
    Register_Doctor,
    Login_Email_and_Password,
    Login_Mobile_Number_otp_sent,
    Login_Mobile_Number_verify,
    Chaining_Password,
    Forget_Password_otp_Sent,
    Forge_Password_Save,
    DoctorAvailabilityAPIView,
)

urlpatterns = [
    path("registervalidate/", Register_Validate.as_view()),
    path("userregistersave/", Register_User.as_view()),
    path("doctorregistersave/", Register_Doctor.as_view()),
    path("loginemailandpassword/", Login_Email_and_Password.as_view()),
    path("loginemobilenumberverify/", Login_Mobile_Number_verify.as_view()),
    path("loginmobilenumberotpsent/", Login_Mobile_Number_otp_sent.as_view()),
    path("chainigpassword/", Chaining_Password.as_view()),
    path("forgetpasswordotpsent/", Forget_Password_otp_Sent.as_view()),
    path("forgetpasswordsave/", Forge_Password_Save.as_view()),
    path(
        "doctor_availability/",
        DoctorAvailabilityAPIView.as_view(),
        name="doctor_availability",
    ),
]
