from rest_framework import serializers
from .models import UserProfile
import re
class RegisterValidateSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField(required=True)

    class Meta:
        model = UserProfile
        fields = (
            "email",
            "mobile_number",
            "password",
            "password2"
        )

    def validate(self, attrs):
        password = attrs.get("password")
        password2 = attrs.get("password2")

        # Check if password and password2 match

        # Validate password strength
        if len(password) < 8:
            raise serializers.ValidationError(
                {"password": "Password must be at least 8 characters long."}
            )

        if not re.search(r"[A-Za-z]", password):
            raise serializers.ValidationError(
                {"password": "Password must contain at least one alphabetic character."}
            )

        if not re.search(r"[0-9]", password):
            raise serializers.ValidationError(
                {"password": "Password must contain at least one numeric character."}
            )

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise serializers.ValidationError(
                {"password": "Password must contain at least one special character."}
            )
        if password != password2:
            raise serializers.ValidationError({"Error": "Passwords do not match."})

        return attrs
    
from rest_framework import serializers
from .models import UserProfile

class Register_User_Data(serializers.ModelSerializer):
    otp = serializers.CharField(required=True)
    password2 = serializers.CharField(required=True, write_only=True)  # Ensure it's not returned in response

    class Meta:
        model = UserProfile
        fields = (
            "email",
            "mobile_number",
            "password",
            "password2",
            # "profile_pic",
            # "medical_report",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "height",
            "weight",
            "blood_group",
            "otp"
        )

    def validate(self, attrs):
        password = attrs.get("password")
        password2 = attrs.get("password2")

        if password != password2:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        return attrs  # Make sure to return attrs

    def create(self, validated_data):
        validated_data.pop("password2")  # Remove password2 before saving
        otp = validated_data.pop("otp")  # OTP should not be stored in the database

        # Create user object
        user = UserProfile.objects.create(**validated_data)
        user.set_password(validated_data["password"])  # Hash the password
        user.save()

        return user  # Return the saved user object
