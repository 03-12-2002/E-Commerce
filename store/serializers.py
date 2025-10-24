from rest_framework import serializers
from .models import *
from catalogs.models import Product, ProductVariation
from catalogs.serializers import ProductSerializer, ProductVariationSerializer

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    variation = ProductVariationSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product_id", "product_name", "variation", "qty", "price_at_add", "image", "line_total"]

    def get_image(self, obj):
        first = obj.product.images.first()
        request = self.context.get("request")
        if first:
            if request:
                return request.build_absolute_uri(first.image.url)
            return first.image.url
        return None

    def get_line_total(self, obj):
        return str(obj.line_total())

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "user_id", "items", "total_price"]
        read_only_fields = ["id", "user_id", "items", "total_price"]

    def get_total_price(self, obj):
        return str(obj.total_price())

class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    variation_id = serializers.IntegerField(required=False, allow_null=True)
    qty = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        try:
            data["product"] = Product.objects.get(pk=data["product_id"])
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_id": "Product not found."})
        variation_id = data.get("variation_id")
        if variation_id:
            try:
                data["variation"] = ProductVariation.objects.get(pk=variation_id, product=data["product"])
            except ProductVariation.DoesNotExist:
                raise serializers.ValidationError({"variation_id": "Variation not found for this product."})
        else:
            data["variation"] = None
        return data

class RemoveFromCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=False)
    variation_id = serializers.IntegerField(required=False)
    cart_item_id = serializers.IntegerField(required=False)

class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "product", "added_at"]

class AddToWishlistSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()

    def validate(self, data):
        try:
            data["product"] = Product.objects.get(pk=data["product_id"])
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_id": "Product not found."})
        return data

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    variation = ProductVariationSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "variation", "qty", "price_at_order"]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user_id", "total_amount", "status", "razorpay_order_id", "razorpay_payment_id", "created_at", "items"]
        read_only_fields = ["id", "user_id", "status", "created_at", "items"]