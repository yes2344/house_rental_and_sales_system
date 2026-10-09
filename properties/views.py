from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny

from accounts.permissions import (
    IsListingManager,
    IsPropertyManagerOrAdministrator,
)
from properties.access import managed_properties
from properties.filters import PublicPropertyFilter
from properties.models import Amenity, Property, PropertyImage
from properties.serializers import (
    AmenitySerializer,
    PropertyImageManagementSerializer,
    PropertyManagementSerializer,
    PublicPropertyDetailSerializer,
    PublicPropertyListSerializer,
)


PUBLIC_STATUSES = [Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE]


class PublicAmenityListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AmenitySerializer
    queryset = Amenity.objects.all().order_by('name')

    @extend_schema(summary='List amenities available for property listings')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicPropertyListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicPropertyListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PublicPropertyFilter
    search_fields = ['title', 'location', 'description', 'features', 'amenities__name']
    ordering_fields = ['created_at', 'price', 'bedrooms', 'bathrooms', 'area_sqft']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            Property.objects.filter(
                publication_status=Property.PublicationStatus.PUBLISHED,
                status__in=PUBLIC_STATUSES,
            )
            .prefetch_related('images', 'amenities')
            .order_by(*self.ordering)
        )

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).distinct()

    @extend_schema(
        summary='Browse available published properties',
        description=(
            'Search with `search`; filter by `listing_type`, `property_type`, `status`, '
            '`min_price`, `max_price`, bedroom/bathroom ranges, size ranges, and comma-separated '
            'amenity slugs. Public results always exclude unpublished, rented, sold, and inactive listings.'
        ),
        responses=PublicPropertyListSerializer(many=True),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicPropertyDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicPropertyDetailSerializer
    lookup_field = 'slug'
    queryset = (
        Property.objects.filter(
            publication_status=Property.PublicationStatus.PUBLISHED,
            status__in=PUBLIC_STATUSES,
        )
        .prefetch_related('images', 'amenities')
    )

    @extend_schema(summary='Retrieve a published available property')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ManagedPropertyListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsListingManager]
    serializer_class = PropertyManagementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'publication_status', 'listing_type', 'property_type']
    search_fields = ['title', 'location', 'description']
    ordering_fields = ['created_at', 'updated_at', 'price']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            managed_properties(self.request.user)
            .select_related('owner')
            .prefetch_related('amenities', 'images')
        )


class ManagedPropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPropertyManagerOrAdministrator]
    serializer_class = PropertyManagementSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return (
            managed_properties(self.request.user)
            .select_related('owner')
            .prefetch_related('amenities', 'images')
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        for image in instance.images.all():
            image.image.delete(save=False)
        instance.delete()


class ManagedPropertyImageListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsListingManager]
    serializer_class = PropertyImageManagementSerializer
    queryset = PropertyImage.objects.none()

    def get_property_queryset(self):
        return managed_properties(self.request.user)

    def get_queryset(self):
        return PropertyImage.objects.filter(
            property__in=self.get_property_queryset(),
            property_id=self.kwargs['property_id'],
        ).select_related('property')

    @transaction.atomic
    def perform_create(self, serializer):
        property_obj = get_object_or_404(
            self.get_property_queryset().select_for_update(),
            pk=self.kwargs['property_id'],
        )
        image_count = property_obj.images.count()
        if image_count >= 10:
            raise ValidationError({'image': 'A property can have at most 10 images.'})

        is_primary = serializer.validated_data.get('is_primary', image_count == 0)
        if image_count == 0:
            is_primary = True
        if is_primary:
            property_obj.images.update(is_primary=False)
        serializer.save(property=property_obj, is_primary=is_primary)


class ManagedPropertyImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsListingManager]
    serializer_class = PropertyImageManagementSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return PropertyImage.objects.filter(
            property__in=managed_properties(self.request.user),
            property_id=self.kwargs['property_id'],
        ).select_related('property')

    @transaction.atomic
    def perform_update(self, serializer):
        image = self.get_object()
        property_obj = get_object_or_404(
            managed_properties(self.request.user).select_for_update(),
            pk=self.kwargs['property_id'],
        )
        if serializer.validated_data.get('is_primary', image.is_primary):
            property_obj.images.exclude(pk=image.pk).update(is_primary=False)
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.image.delete(save=False)
        instance.delete()
