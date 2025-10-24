from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response
from .models import Cart, CartItem, WishlistItem, Order, OrderItem
from .serializers import (
    CartSerializer, AddToCartSerializer, RemoveFromCartSerializer, CartItemSerializer,
    WishlistSerializer, AddToWishlistSerializer, OrderSerializer
)
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db import transaction
from django.conf import settings
import hmac, hashlib, random, string
import razorpay

# Utility to get or create a user's cart
def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart

# CART endpoints
class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)

class CartAddView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = get_or_create_cart(request.user)
        product = data["product"]
        variation = data.get("variation")
        qty = data.get("qty", 1)
        # determine price_at_add: variation.price if set else product.price
        price = variation.price if (variation and variation.price is not None) else product.price
        # check existing item
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, variation=variation,
                                                            defaults={"qty": qty, "price_at_add": price})
        if not created:
            cart_item.qty += qty
            cart_item.save()
        return Response({"detail": "Added to cart."}, status=status.HTTP_200_OK)

class CartRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RemoveFromCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = get_or_create_cart(request.user)
        if data.get("cart_item_id"):
            try:
                item = CartItem.objects.get(pk=data["cart_item_id"], cart=cart)
                item.delete()
            except CartItem.DoesNotExist:
                return Response({"detail": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"detail": "Removed from cart."})
        # else try remove by product+variation
        product_id = data.get("product_id")
        variation_id = data.get("variation_id")
        if not product_id:
            return Response({"detail": "Provide cart_item_id or product_id."}, status=status.HTTP_400_BAD_REQUEST)
        qs = CartItem.objects.filter(cart=cart, product_id=product_id)
        if variation_id is not None:
            qs = qs.filter(variation_id=variation_id)
        deleted, _ = qs.delete()
        if deleted:
            return Response({"detail": "Removed from cart."})
        return Response({"detail": "No matching cart items found."}, status=status.HTTP_404_NOT_FOUND)

class CartClearView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart = get_or_create_cart(request.user)
        cart.items.all().delete()
        return Response({"detail": "Cart cleared."})

# WISHLIST endpoints
class WishlistListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = WishlistItem.objects.filter(user=request.user).select_related("product")
        serializer = WishlistSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

class WishlistAddView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddToWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        obj, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
        if created:
            return Response({"detail": "Added to wishlist."})
        return Response({"detail": "Already in wishlist."})

class WishlistRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"detail": "Provide product_id."}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
        if deleted:
            return Response({"detail": "Removed from wishlist."})
        return Response({"detail": "Not found in wishlist."}, status=status.HTTP_404_NOT_FOUND)

# ORDERS
class PlaceOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Place an order from cart contents.
        Returns created order object with total_amount.
        Client is expected to create a payment via Razorpay frontend and then call verify endpoint,
        but for our backend-only flow we create order and return its id (and you may optionally set razorpay_order_id).
        """
        cart = get_or_create_cart(request.user)
        items = cart.items.select_related("product", "variation").all()
        if not items.exists():
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        total = Decimal("0.00")
        for it in items:
            total += it.line_total()

        order = Order.objects.create(user=request.user, total_amount=total, status="PENDING")
        # create order items
        for it in items:
            OrderItem.objects.create(order=order, product=it.product, variation=it.variation, qty=it.qty, price_at_order=it.price_at_add)
        
        # --- Razorpay Order Creation ---
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create({
                "amount": int(total * 100),  # Razorpay expects amount in paise
                "currency": "INR",
                "payment_capture": 1,  # auto capture
                "notes": {"local_order_id": str(order.id), "user": request.user.email},
            })
            order.razorpay_order_id = razorpay_order.get("id")
            order.save()
        except Exception as e:
            # if Razorpay API fails, delete order
            order.delete()
            return Response(
                {"detail": f"Razorpay order creation failed: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response({"detail": "Order created.", "order_id": order.id, "total_amount": str(total), "razorpay_order_id": order.razorpay_order_id, "currency": "INR", "razorpay_data": razorpay_order}, status=status.HTTP_201_CREATED)

class ListOrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Order.objects.filter(user=request.user).prefetch_related("items__product")
        serializer = OrderSerializer(qs, many=True)
        return Response(serializer.data)

class VerifyRazorpayPaymentView(APIView):
    """
    Verifies Razorpay payment signatures (production-ready).
    Compatible with terminal_verification_razorpay.py for test verification.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        required = ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature", "order_id"]
        if not all(k in data for k in required):
            return Response({"detail": f"Required fields: {required}"}, status=status.HTTP_400_BAD_REQUEST)

        razorpay_order_id = data["razorpay_order_id"]
        razorpay_payment_id = data["razorpay_payment_id"]
        signature = data["razorpay_signature"]
        local_order_id = data["order_id"]

        # Verify via Razorpay SDK (production-safe)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": signature
            })
        except razorpay.errors.SignatureVerificationError:
            # mark as failed
            try:
                order = Order.objects.get(id=local_order_id, user=request.user)
                order.status = "FAILED"
                order.razorpay_order_id = razorpay_order_id
                order.razorpay_payment_id = razorpay_payment_id
                order.razorpay_signature = signature
                order.save()
            except Order.DoesNotExist:
                pass
            return Response({"detail": "Invalid Razorpay signature."}, status=status.HTTP_400_BAD_REQUEST)

        # If valid signature
        try:
            order = Order.objects.get(id=local_order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Local order not found."}, status=status.HTTP_404_NOT_FOUND)

        order.status = "PAID"
        order.razorpay_order_id = razorpay_order_id
        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_signature = signature
        order.save()

        # Clear cart
        cart = get_or_create_cart(request.user)
        for item in order.items.all():
            CartItem.objects.filter(cart=cart, product=item.product, variation=item.variation).delete()

        return Response({
            "detail": "Payment verified successfully.",
            "order_id": order.id,
            "status": order.status
        }, status=status.HTTP_200_OK)
