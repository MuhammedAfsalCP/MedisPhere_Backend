from rest_framework import serializers
from .models import UserProfile
import re


class RegisterValidateSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField(required=True)

    class Meta:
        model = UserProfile
        fields = ("email", "mobile_number", "password", "password2")

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
    password2 = serializers.CharField(
        required=True, write_only=True
    )  # Ensure it's not returned in response

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
            "otp",
        )

    def validate(self, attrs):
        password = attrs.get("password")
        password2 = attrs.get("password2")

        if password != password2:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        return attrs  # Make sure to return attrs

    def create(self, validated_data):
        validated_data.pop("password2")  # Remove password2 before saving
        otp = validated_data.pop("otp")
        password = validated_data.pop(
            "password"
        )  # OTP should not be stored in the database

        # Create user object
        user = UserProfile.objects.create_user(
            **validated_data, password=password
        )  # Hash the password
        user.save()

        return user  # Return the saved user object


class Register_Doctor_Data(serializers.ModelSerializer):
    otp = serializers.CharField(required=True)
    password2 = serializers.CharField(
        required=True, write_only=True
    )  # Ensure it's not returned in response

    class Meta:
        model = UserProfile
        fields = (
            "email",
            "mobile_number",
            "password",
            "password2",
            # "profile_pic",
            # "license_photo",
            "first_name",
            "last_name",
            "department",
            "gender",
            "years_of_experiance",
            "license_number",
            "consultation_fee",
            "upi_id",
            "otp",
        )

    def validate(self, attrs):
        password = attrs.get("password")
        password2 = attrs.get("password2")

        if password != password2:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        return attrs  # Make sure to return attrs

    def create(self, validated_data):
        validated_data.pop("password2")  # Remove password2 before saving
        otp = validated_data.pop("otp")
        password = validated_data.pop(
            "password"
        )  # OTP should not be stored in the database

        # Create user object
        user = UserProfile.objects.create_user(
            **validated_data, password=password, is_doctor=True
        )
        user.save()
        return user  # Return the saved user object


class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "mobile_number",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_doctor",
        )


class ChainingPasswordSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(required=True, write_only=True)
    ConfirmationPassword = serializers.CharField(required=True, write_only=True)
    checkemail = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = UserProfile
        fields = ("checkemail", "password", "password2", "ConfirmationPassword")

    def validate(self, attrs):
        password = attrs.get("ConfirmationPassword")
        password2 = attrs.get("password2")

        if password != password2:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        return attrs  # Make sure to return attrs

    def create(self, validated_data):
        checkemail = validated_data.get("checkemail")  # Get email from validated data

        try:
            user = UserProfile.objects.get(email=checkemail)  # Fetch user by email
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                {"email": "User with this email does not exist."}
            )

        password = validated_data.get("ConfirmationPassword")
        user.set_password(password)  # Update the user's password securely
        user.save()

        return user  # Return updated user


class ForgetPasswordSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(required=True, write_only=True)
    ConfirmationPassword = serializers.CharField(required=True, write_only=True)
    checkmobile = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = UserProfile
        fields = ("checkmobile", "password2", "ConfirmationPassword")

    def validate(self, attrs):
        password = attrs.get("ConfirmationPassword")
        password2 = attrs.get("password2")

        if password != password2:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        return attrs  # Make sure to return attrs

    def create(self, validated_data):
        checkmobile = validated_data.get("checkmobile")  # Get email from validated data

        try:
            user = UserProfile.objects.get(
                mobile_number=checkmobile
            )  # Fetch user by email
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                {"email": "User with this email does not exist."}
            )

        password = validated_data.get("ConfirmationPassword")
        user.set_password(password)  # Update the user's password securely
        user.save()

        return user  # Return updated user
