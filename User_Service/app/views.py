from django.core.cache import cache  # For temporary storage
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import UserProfile, DoctorAvailability
from rest_framework_simplejwt.tokens import RefreshToken
import base64
from django.core.files.base import ContentFile
from rest_framework.permissions import AllowAny, IsAdminUser
from django.contrib.auth import authenticate
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .permissions import IsDoctor, IsAdmin, IsStaff, IsPatient
from .utils import send_otp
from .serializer import (
    RegisterValidateSerializer,
    Register_User_Data,
    Register_Doctor_Data,
    LoginSerializer,
    ChainingPasswordSerializer,
    ForgetPasswordSerializer,
    UserDetailSerializer,
    AppointmentHistorySerializer,
    PatientDetailsSerializer,
)
import pika
import json


class Register_Validate(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterValidateSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            phone = serializer.validated_data.get("mobile_number")
            response = send_otp(phone)

            if response.get("success"):  # Ensure OTP was sent successfully
                return Response(response, status=status.HTTP_200_OK)
            else:
                return Response(response, status=status.HTTP_400_BAD_REQUEST)


class Register_User(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = Register_User_Data(data=request.data)

        if serializer.is_valid():
            phone = serializer.validated_data.get("mobile_number")
            otp_entered = serializer.validated_data.get("otp")

            stored_otp = cache.get(f"otp_{phone}")  # Retrieve OTP from cache

            if stored_otp is None:
                return Response(
                    {"error": "OTP expired or not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if stored_otp == otp_entered:
                cache.delete(f"otp_{phone}")
                serializer.save()
                return Response(
                    {"message": "User registered successfully"},
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Register_Doctor(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = Register_Doctor_Data(data=request.data)

        if serializer.is_valid():
            phone = serializer.validated_data.get("mobile_number")
            otp_entered = serializer.validated_data.get("otp")

            stored_otp = cache.get(f"otp_{phone}")  # Retrieve OTP from cache

            if stored_otp is None:
                return Response(
                    {"error": "OTP expired or not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if stored_otp == otp_entered:
                cache.delete(f"otp_{phone}")  # OTP is correct, remove it from cache
                serializer.save()  # Save the user
                return Response(
                    {"message": "Doctor registered successfully"},
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Login_Email_and_Password(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(email=email, password=password)

        if user is not None:

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            userdetail = UserProfile.objects.get(email=email)
            serializer = LoginSerializer(userdetail)
            return Response(
                {
                    "access": access_token,
                    "refresh": str(refresh),
                    "userdetail": serializer.data,
                }
            )
        else:

            return Response(
                {"error": "invaliduser"}, status=status.HTTP_401_UNAUTHORIZED
            )


class Login_Mobile_Number_otp_sent(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("mobile_number")
        user = UserProfile.objects.get(mobile_number=phone)

        if user is not None:
            response = send_otp(phone)

            if response.get("success"):  # Ensure OTP was sent successfully
                return Response(response, status=status.HTTP_200_OK)
            else:
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
        else:

            return Response(
                {"error": "invaliduser"}, status=status.HTTP_401_UNAUTHORIZED
            )


class Login_Mobile_Number_verify(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("mobile_number")
        otp_entered = request.data.get("otp")

        stored_otp = cache.get(f"otp_{phone}")  # Retrieve OTP from cache

        if stored_otp is None:
            return Response(
                {"error": "OTP expired or not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if stored_otp == otp_entered:
            userdetail = UserProfile.objects.get(mobile_number=phone)
            refresh = RefreshToken.for_user(userdetail)
            access_token = str(refresh.access_token)
            serializer = LoginSerializer(userdetail)
            cache.delete(f"otp_{phone}")
            return Response(
                {
                    "access": access_token,
                    "refresh": str(refresh),
                    "userdetail": serializer.data,
                }
            )
        else:

            return Response(
                {"error": "invaliduser"}, status=status.HTTP_401_UNAUTHORIZED
            )


class Chaining_Password(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ChainingPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"message": "Password updated successfully."}, status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Forget_Password_otp_Sent(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("mobile_number")
        user = UserProfile.objects.get(mobile_number=phone)

        if user is not None:
            response = send_otp(phone)

            if response.get("success"):  # Ensure OTP was sent successfully
                return Response(response, status=status.HTTP_200_OK)
            else:
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response(
                {"error": "invaliduser"}, status=status.HTTP_401_UNAUTHORIZED
            )


class Forge_Password_Save(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("checkmobile")
        otp_entered = request.data.get("otp")

        stored_otp = cache.get(f"otp_{phone}")  # Retrieve OTP from cache

        if stored_otp is None:
            return Response(
                {"error": "OTP expired or not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if stored_otp == otp_entered:
            serializer = ForgetPasswordSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                return Response(
                    {"message": "Password updated successfully."},
                    status=status.HTTP_200_OK,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorAvailabilityAPIView(APIView):
    """API to check doctor availability"""

    def post(self, request):
        data = request.data
        doctor_firstname = data.get("doctor_name")
        date = data.get("date")
        slot = data.get("slot")

        try:
            doctor = UserProfile.objects.get(
                first_name=doctor_firstname, is_doctor=True
            )
            availability = DoctorAvailability.objects.filter(
                doctor=doctor, date=date, slot=slot, is_available=True
            )

            if availability:
                return Response(
                    {
                        "available": True,
                        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
                    }
                )
            else:
                return Response(
                    {
                        "available": False,
                        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
                    }
                )

        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND
            )


class UserDetailsGet(APIView):

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "User not authenticated"}, status=401)
        serializer=UserDetailSerializer(instance=user)  # `request.user` is populated by JWTAuthentication
        return Response({"userdetail": serializer.data})
    
class AppointmentHistory(APIView):
    permission_classes=[IsPatient]
    def get(self,request):
        user=request.user
        History=DoctorAvailability.objects.filter(patient__email=user.email).select_related("doctor")
        if not History.exists():
                return Response(
                    {"message": "No appointment history found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        serializer=AppointmentHistorySerializer(History,many=True)
        return Response({"History": serializer.data})


class PatientDetials(APIView):
    # permission_classes=[IsPatient]
    def get(self,request):
        user=request.user
        
        try:
            User=UserProfile.objects.get(email=user.email)
                

        except:
            return Response(
                    {"message": "No user found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        serializer=PatientDetailsSerializer(User)
        return Response({"User": serializer.data})
    def put(self, request):
        try:
            # Get the authenticated user
            user = request.user
            data = request.data.copy()  # Create a mutable copy of request.data

            # Handle file upload (e.g., profile picture) if included
            if 'avatar' in data and data['avatar']:
                # Assuming avatar is sent as base64 string
                format, imgstr = data['avatar'].split(';base64,')
                ext = format.split('/')[-1]  # Get extension (e.g., 'png', 'jpg')
                filename = f"{user.id}_profile.{ext}"
                avatar_data = ContentFile(
                    base64.b64decode(imgstr),
                    name=filename
                )
                data['avatar'] = avatar_data
            else:
                # Remove avatar from data if not provided to avoid overwriting with empty value
                data.pop('avatar', None)

            # Serialize and update user data
            serializer = PatientDetailsSerializer(
                instance=user,
                data=data,
                partial=True  # Allow partial updates
            )

            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Profile updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'Invalid data',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'message': 'An error occurred while updating profile',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
import logging
logger = logging.getLogger('django')

