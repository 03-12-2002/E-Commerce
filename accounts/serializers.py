# ecom_project/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate, password_validation, get_user_model
from .models import OTP
from .utils import generate_otp_code, send_otp_via_email
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        # validate password strength
        try:
            password_validation.validate_password(data["password"], user=None)
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        if User.objects.filter(email__iexact=data["email"]).exists():
            raise serializers.ValidationError({"email": "User with this email already exists."})
        if User.objects.filter(phone_number=data["phone_number"]).exists():
            raise serializers.ValidationError({"phone_number": "User with this phone number already exists."})
        return data

    def create(self, validated_data):
        # create inactive user
        user = User.objects.create_user(
            email=validated_data["email"],
            phone_number=validated_data["phone_number"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=validated_data["password"],
        )
        user.is_active = False
        user.save()
        # create OTP
        code = generate_otp_code()
        otp = OTP.objects.create(email=user.email, code=code, purpose="signup", expires_at=timezone.now() + timedelta(minutes=10))
        # send email (console)
        send_otp_via_email(user.email, code, "Signup")
        return user

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(choices=OTP.PURPOSE_CHOICES)
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            otp_obj = OTP.objects.filter(email__iexact=data["email"], purpose=data["purpose"], is_verified=False).order_by("-created_at").first()
            if not otp_obj:
                raise serializers.ValidationError({"otp": "No OTP found for this email and purpose."})
            if otp_obj.is_expired():
                raise serializers.ValidationError({"otp": "OTP has expired."})
            if otp_obj.code != data["otp"]:
                raise serializers.ValidationError({"otp": "Invalid OTP code."})
            data["otp_obj"] = otp_obj
            return data
        except OTP.DoesNotExist:
            raise serializers.ValidationError({"otp": "OTP not found."})

    def save(self):
        otp_obj = self.validated_data["otp_obj"]
        otp_obj.is_verified = True
        otp_obj.save()
        # If purpose is signup -> activate user
        if otp_obj.purpose == "signup":
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(email__iexact=otp_obj.email)
                user.is_active = True
                user.save()
            except User.DoesNotExist:
                pass
        return otp_obj

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(choices=OTP.PURPOSE_CHOICES)

    def validate(self, data):
        # if purpose is signup and user already active -> can't resend
        if data["purpose"] == "signup":
            qs = User.objects.filter(email__iexact=data["email"])
            if qs.exists() and qs.first().is_active:
                raise serializers.ValidationError({"email": "Account already active."})
        return data

    def save(self):
        code = generate_otp_code()
        otp = OTP.objects.create(email=self.validated_data["email"], code=code, purpose=self.validated_data["purpose"],
                                 expires_at=timezone.now() + timedelta(minutes=10))
        send_otp_via_email(self.validated_data["email"], code, f"Resend OTP ({self.validated_data['purpose']})")
        return otp

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("No user with this email.")
        return value

    def save(self):
        code = generate_otp_code()
        otp = OTP.objects.create(email=self.validated_data["email"], code=code, purpose="reset", expires_at=timezone.now() + timedelta(minutes=10))
        send_otp_via_email(self.validated_data["email"], code, "Password Reset")
        return otp

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        try:
            # Must have a verified OTP for reset
            otp_obj = OTP.objects.filter(email__iexact=data["email"], purpose="reset", is_verified=True).order_by("-created_at").first()
            if not otp_obj:
                raise serializers.ValidationError({"otp": "No verified OTP found for this email. Please verify OTP first."})
            if otp_obj.is_expired():
                raise serializers.ValidationError({"otp": "OTP has expired."})
            data["otp_obj"] = otp_obj
        except OTP.DoesNotExist:
            raise serializers.ValidationError({"otp": "No verified OTP found."})
        # validate password strength
        try:
            password_validation.validate_password(data["new_password"], user=None)
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return data

    def save(self):
        email = self.validated_data["email"]
        new_password = self.validated_data["new_password"]
        user = User.objects.get(email__iexact=email)
        user.set_password(new_password)
        user.save()
        # consume OTP
        otp_obj = self.validated_data["otp_obj"]
        otp_obj.is_verified = False
        otp_obj.save()
        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "New passwords do not match."})
        try:
            password_validation.validate_password(data["new_password"], user=self.context["request"].user)
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return data

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
