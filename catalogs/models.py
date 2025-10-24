from django.db import models
from django.utils.text import slugify
from django.utils import timezone
import uuid

class Category(models.Model):
    # Integer primary key (default)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:120]
            slug_candidate = base
            num = 1
            while Category.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                slug_candidate = f"{base}-{num}"
                num += 1
            self.slug = slug_candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:240]
            slug_candidate = base
            num = 1
            while Product.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                slug_candidate = f"{base}-{num}"
                num += 1
            self.slug = slug_candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="product_images/")
    alt_text = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"

class ProductVariation(models.Model):
    """
    Represents a variation (combination) for a product.
    Either color or size or both can be provided.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variations")
    color = models.CharField(max_length=64, blank=True, null=True)
    size = models.CharField(max_length=32, blank=True, null=True)
    # sku = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                help_text="Optional override price for this variation (if empty uses product.price)")
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = (("product", "color", "size"),)
        ordering = ["id"]

    def __str__(self):
        parts = []
        if self.color:
            parts.append(self.color)
        if self.size:
            parts.append(self.size)
        return f"{self.product.name} - {'/'.join(parts) if parts else 'Default'}"
