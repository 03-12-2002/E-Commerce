# ecom_project/accounts/urls.py
from django.urls import path
from .views import (
    SignupView, VerifyOTPView, ResendOTPView, EmailTokenObtainPairView,
    ForgotPasswordView, ResetPasswordView, ChangePasswordView
)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("login/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
