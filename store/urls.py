from django.urls import path
from .views import *

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart-detail"),
    path("cart/add/", CartAddView.as_view(), name="cart-add"),
    path("cart/remove/", CartRemoveView.as_view(), name="cart-remove"),
    path("cart/clear/", CartClearView.as_view(), name="cart-clear"),
    path("wishlist/", WishlistListView.as_view(), name="wishlist-list"),
    path("wishlist/add/", WishlistAddView.as_view(), name="wishlist-add"),
    path("wishlist/remove/", WishlistRemoveView.as_view(), name="wishlist-remove"),
    path("orders/place/", PlaceOrderView.as_view(), name="orders-place"),
    path("orders/", ListOrdersView.as_view(), name="orders-list"),
    path("orders/verify-payment/", VerifyRazorpayPaymentView.as_view(), name="orders-verify"),
]
