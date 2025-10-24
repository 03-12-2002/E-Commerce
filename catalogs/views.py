from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Category, Product, ProductImage
from .serializers import CategorySerializer, ProductSerializer, ProductCreateUpdateSerializer, ProductImageSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

class IsAdminOrReadOnlyForAuthenticated:
    """
    Custom permission-like helper used in viewset methods:
      - Allow SAFE_METHODS (GET, HEAD, OPTIONS) for any authenticated user.
      - Require admin (is_staff) for POST, PUT, PATCH, DELETE.
    We'll enforce inside our viewsets by checking request.method and request.user.is_staff,
    while still using IsAuthenticated as base permission.
    """
    pass

# Category ViewSet
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]  # base: only authenticated users can access endpoints

    def get_permissions(self):
        # already enforced by permission_classes; but we need role-based behavior:
        # Allow any authenticated user to list/retrieve (GET). For others require admin.
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

# Product ViewSet
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.prefetch_related("images", "variations").all()
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"]:
            return ProductCreateUpdateSerializer
        return ProductSerializer
    
    def list(self, request, *args, **kwargs):
        """
        Optionally filter by ?category=<id_or_slug>
        """
        qs = self.get_queryset()
        category_q = request.query_params.get("category")
        if category_q:
            # try id first
            if category_q.isdigit():
                qs = qs.filter(category__id=int(category_q))
            else:
                qs = qs.filter(category__slug=category_q)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ProductSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = ProductSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ProductSerializer(instance, context={"request": request})
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # Admin-only
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        # handle images: expect multiple files under key 'images'
        images = request.FILES.getlist("images")
        for img in images:
            ProductImage.objects.create(product=product, image=img)
        # return full product representation
        read_serializer = ProductSerializer(product, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        # Admin-only
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        # handle images if provided: if images present, append them (do not delete existing)
        images = request.FILES.getlist("images")
        for img in images:
            ProductImage.objects.create(product=product, image=img)

        read_serializer = ProductSerializer(product, context={"request": request})
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    # Optionally allow admin to delete a specific image via a nested action:
    @action(detail=True, methods=["delete"], url_path="images/(?P<img_id>[^/.]+)", permission_classes=[IsAuthenticated])
    def delete_image(self, request, pk=None, img_id=None):
        # admin-only
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        product = self.get_object()
        img = get_object_or_404(ProductImage, pk=img_id, product=product)
        img.delete()
        return Response({"detail": "Image deleted."}, status=status.HTTP_204_NO_CONTENT)
