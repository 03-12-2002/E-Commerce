# <start of file> ecom_project/store/admin.py
from django.contrib import admin
from .models import Cart, CartItem, WishlistItem, Order, OrderItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "updated_at")
    inlines = [CartItemInline]

@admin.register(WishlistItem)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "added_at")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_amount", "status", "created_at")
    inlines = [OrderItemInline]
# <end of file>
