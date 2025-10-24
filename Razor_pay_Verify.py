#Paste this " exec(open("Razor_pay_Verify.py").read())" on shell

import hmac, hashlib, random, string
from django.conf import settings
razorpay_payment_id = "pay_" + ''.join(random.choices(string.ascii_letters + string.digits, k=14))
razorpay_order_id = "order_RXN1ZzT5JNSbfq" # Paste your razorpay_order_id here
generated_signature = hmac.new(
    settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
    f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8"),
    hashlib.sha256
).hexdigest()
print("order_id:", razorpay_order_id)
print("payment_id:", razorpay_payment_id)
print("signature:", generated_signature)