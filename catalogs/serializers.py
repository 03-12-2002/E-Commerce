from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductVariation
from django.db import transaction
import json

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "slug", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

class ProductVariationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariation
        fields = ["id", "color", "size", "price", "is_available"]# "sku",
        read_only_fields = ["id"]

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variations = ProductVariationSerializer(many=True, read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    representative_image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "is_available", "category", "slug", "images", "representative_image", "variations", "created_at"]
        read_only_fields = ["id", "slug", "images", "representative_image", "variations", "created_at"]

    def get_representative_image(self, obj):
        first = obj.images.first()
        if first:
            request = self.context.get("request")
            # image.url returns the relative URL; include request.build_absolute_uri if request present
            if request:
                return request.build_absolute_uri(first.image.url)
            return first.image.url
        return None

    def to_internal_value(self, data):
        # handle JSON string for variations if provided in form-data
        data = super().to_internal_value(data)
        return data

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer used for create/update via API.
    Accepts:
      - 'images' as multiple uploaded files (handled in view)
      - 'variations' as a JSON array (string in form-data) OR as JSON list if request is application/json
        Example variations JSON:
        [
          {"color": "Red", "size": "M", "price": "299.99", "is_available": true}, "sku": "R-M-001", 
          {"color": "Red", "size": "L", "price": "299.99", "is_available": true}  "sku": "R-L-001", 
        ]
    """
    # images not declared here; handled in view from request.FILES.getlist('images')
    variations = serializers.JSONField(required=False)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "is_available", "category", "variations"]
        read_only_fields = ["id"]

    def validate_variations(self, value):
        # ensure it's a list of objects if provided
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                raise serializers.ValidationError("Invalid JSON for variations.")
        if not isinstance(value, list):
            raise serializers.ValidationError("Variations must be a list.")
        # further optional validation can be added
        return value

    @transaction.atomic
    def create(self, validated_data):
        variations_data = validated_data.pop("variations", [])
        product = Product.objects.create(**validated_data)
        # create variations if any
        for v in variations_data:
            ProductVariation.objects.create(
                product=product,
                color=v.get("color"),
                size=v.get("size"),
                # sku=v.get("sku"),
                price=v.get("price") if v.get("price") not in (None, "") else None,
                is_available=v.get("is_available", True),
            )
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        variations_data = validated_data.pop("variations", None)
        # update product fields
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        # if variations provided: replace existing variations with provided set
        if variations_data is not None:
            # delete old
            instance.variations.all().delete()
            for v in variations_data:
                ProductVariation.objects.create(
                    product=instance,
                    color=v.get("color"),
                    size=v.get("size"),
                    # sku=v.get("sku"),
                    price=v.get("price") if v.get("price") not in (None, "") else None,
                    is_available=v.get("is_available", True),
                )
        return instance
