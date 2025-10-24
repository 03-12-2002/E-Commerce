from django.contrib import admin

from django.contrib import admin
from .models import Category, Product, ProductImage, ProductVariation

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "is_available", "category")
    inlines = [ProductImageInline, ProductVariationInline]
    prepopulated_fields = {"slug": ("name",)}

admin.site.register(ProductImage)
admin.site.register(ProductVariation)
