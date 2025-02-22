import random
from django.core.cache import cache  # For temporary storage
from twilio.rest import Client
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import RegisterValidateSerializer,Register_User_Data

class Register_Validate(APIView):
    def post(self, request):
        serializer = RegisterValidateSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

            otp = str(random.randint(100000, 999999))  # Generate a 6-digit OTP
            phone = serializer.validated_data.get('mobile_number')  # Get phone number from request

            # Store OTP in cache with 5 minutes expiration
            cache.set(f'otp_{phone}', otp, timeout=300)  

            message_body = f"Your OTP is {otp}"

            message = client.messages.create(
                body=message_body,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=f"+91{phone}"
            )

            return Response({'message': 'OTP successfully sent'}, status=status.HTTP_200_OK)
class Register_User(APIView):  # ✅ Renamed to avoid confusion
    def post(self, request):
        serializer = Register_User_Data(data=request.data)  # ✅ Using correct serializer

        if serializer.is_valid():
            phone = serializer.validated_data.get('mobile_number')
            otp_entered = serializer.validated_data.get('otp')

            stored_otp = cache.get(f'otp_{phone}')  # Retrieve OTP from cache

            if stored_otp is None:
                return Response({'error': 'OTP expired or not found'}, status=status.HTTP_400_BAD_REQUEST)

            if stored_otp == otp_entered:
                cache.delete(f'otp_{phone}')  # OTP is correct, remove it from cache
                serializer.save()  # Save the user
                return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)

            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)