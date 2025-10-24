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
        fields = ["id", "color", "size", "price", "is_available"]
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
        request = self.context.get("request")
        if obj.representative_image:
            if request:
                return request.build_absolute_uri(obj.representative_image.url)
            return obj.representative_image.url
        
        first = obj.images.first()
        if first:
            if request:
                return request.build_absolute_uri(first.image.url)
            return first.image.url
        return None

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return data

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    variations = serializers.JSONField(required=False)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "is_available", "category", "variations"]
        read_only_fields = ["id"]

    def validate_variations(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                raise serializers.ValidationError("Invalid JSON for variations.")
        if not isinstance(value, list):
            raise serializers.ValidationError("Variations must be a list.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        variations_data = validated_data.pop("variations", [])
        # ✅ Default is_available to True if missing
        if "is_available" not in validated_data:
            validated_data["is_available"] = True

        product = Product.objects.create(**validated_data)

        for v in variations_data:
            ProductVariation.objects.create(
                product=product,
                color=v.get("color"),
                size=v.get("size"),
                price=v.get("price") if v.get("price") not in (None, "") else None,
                is_available=v.get("is_available", True),
            )
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        variations_data = validated_data.pop("variations", None)
        # ✅ Default is_available to True if missing
        if "is_available" not in validated_data:
            validated_data["is_available"] = True

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if variations_data is not None:
            instance.variations.all().delete()
            for v in variations_data:
                ProductVariation.objects.create(
                    product=instance,
                    color=v.get("color"),
                    size=v.get("size"),
                    price=v.get("price") if v.get("price") not in (None, "") else None,
                    is_available=v.get("is_available", True),
                )
        return instance