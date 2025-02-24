import random
from django.core.cache import cache
from twilio.rest import Client
from django.conf import settings


def send_otp(phone):
    try:
        otp = str(random.randint(100000, 999999))  # Generate OTP
        cache.set(f"otp_{phone}", otp, timeout=300)  # Store OTP in cache

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your OTP is {otp}",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=f"+91{phone}",
        )

        return {"success": True, "message": f"OTP sent to {phone}"}

    except Exception as e:
        return {"success": False, "error": str(e)}  # Always return a response
