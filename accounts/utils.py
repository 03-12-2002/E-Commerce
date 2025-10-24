# ecom_project/accounts/utils.py
import random
from django.core.mail import send_mail
from django.conf import settings

def generate_otp_code(length=6):
    # numeric OTP
    return "".join(str(random.randint(0, 9)) for _ in range(length))

def send_otp_via_email(email, code, purpose):
    subject = f"Your OTP for {purpose}"
    message = f"Your OTP code is: {code}\nIt will expire shortly."
    from_email = settings.DEFAULT_FROM_EMAIL
    # console backend will print to console
    send_mail(subject, message, from_email, [email], fail_silently=False)
