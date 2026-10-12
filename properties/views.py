from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import (
    HasManagementPermission,
    IsAuthenticatedPropertyManagerOrAdministrator,
    IsListingManager,
)
from accounts.models import Profile
from admin.audit import record_admin_action
from properties.access import editable_properties, managed_properties, public_properties
from properties.filters import PublicPropertyFilter
from properties.location_search import matching_location_ids
from properties.models import Amenity, Location, Property, PropertyImage
from properties.search import BilingualPropertySearchFilter
from properties.serializers import (
    AmenitySerializer,
    PropertyImageManagementSerializer,
    PropertyManagementSerializer,
    PublicPropertyDetailSerializer,
    PublicPropertyListSerializer,
    LocationSerializer,
)


PUBLIC_STATUSES = [Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE]


class PublicAmenityListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AmenitySerializer
    queryset = Amenity.objects.all().order_by('name')

    @extend_schema(summary='List amenities available for property listings')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicLocationListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = LocationSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Location.objects.filter(is_active=True)
        search_term = self.request.query_params.get('search', '').strip()
        if search_term:
            return (
                queryset.filter(pk__in=matching_location_ids(search_term))
                .order_by('display_order', 'name')[:20]
            )
        if self.request.query_params.get('all') == '1':
            return queryset.order_by('display_order', 'name')
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            if not Location.objects.filter(pk=parent_id, is_active=True).exists():
                return queryset.none()
            queryset = queryset.filter(parent_id=parent_id)
        else:
            queryset = queryset.filter(parent__isnull=True)
        location_type = self.request.query_params.get('type')
        if location_type:
            queryset = queryset.filter(location_type=location_type)
        return queryset.order_by('display_order', 'name')


class ManagedLocationListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.SETTINGS_MANAGE
    serializer_class = LocationSerializer

    def get_queryset(self):
        queryset = Location.objects.all()
        parent_id = self.request.query_params.get('parent_id')
        return queryset.filter(parent_id=parent_id) if parent_id else queryset.filter(parent__isnull=True)

    def perform_create(self, serializer):
        serializer.save()


class ManagedLocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.SETTINGS_MANAGE
    serializer_class = LocationSerializer
    queryset = Location.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']

    def perform_update(self, serializer):
        serializer.save()


class PublicPropertyListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicPropertyListSerializer
    filter_backends = [DjangoFilterBackend, BilingualPropertySearchFilter, filters.OrderingFilter]
    filterset_class = PublicPropertyFilter
    ordering_fields = ['created_at', 'price', 'bedrooms', 'bathrooms', 'area_sqft']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            public_properties()
            .select_related('submitted_by')
            .prefetch_related(
                'images',
                'amenities',
                'broker_assignments__broker__profile',
            )
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
    queryset = public_properties().select_related('submitted_by').prefetch_related(
        'images',
        'amenities',
        'broker_assignments__broker__profile',
    )

    @extend_schema(summary='Retrieve a published available property')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ManagedPropertyListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedPropertyManagerOrAdministrator]
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

    @transaction.atomic
    def perform_create(self, serializer):
        property_obj = serializer.save()
        record_admin_action(
            self.request.user,
            action='property_created',
            object_type='property',
            object_id=property_obj.pk,
            changes={'publication_status': property_obj.publication_status},
        )


class ManagedPropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedPropertyManagerOrAdministrator]
    serializer_class = PropertyManagementSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return (
            managed_properties(self.request.user)
            .select_related('owner')
            .prefetch_related('amenities', 'images')
        )

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        before_coordinates = (instance.latitude, instance.longitude)
        before = {
            field: getattr(instance, field)
            for field in (
                'status',
                'listing_type',
                'publication_status',
                'exact_location_is_public',
                'contact_publicly_visible',
                'advertising_authorized',
                'area_value',
                'area_unit',
                'rental_frequency',
            )
        }
        updated = serializer.save()
        changes = {}
        for field, old_value in before.items():
            new_value = getattr(updated, field)
            if old_value == new_value:
                continue
            if field in ('contact_publicly_visible', 'advertising_authorized'):
                changes[field] = {'from': old_value, 'to': new_value}
            elif field in ('area_value', 'area_unit', 'rental_frequency', 'status', 'listing_type'):
                changes[field] = {'from': str(old_value), 'to': str(new_value)}
            else:
                changes[field] = {'from': str(old_value), 'to': str(new_value)}
        if before_coordinates != (updated.latitude, updated.longitude):
            changes['coordinates_updated'] = True
        if changes:
            record_admin_action(
                self.request.user,
                action='property_updated',
                object_type='property',
                object_id=updated.pk,
                changes=changes,
            )

    @transaction.atomic
    def perform_destroy(self, instance):
        for image in instance.images.all():
            image.image.delete(save=False)
        instance.delete()


class ManagedPropertyPublicationView(generics.GenericAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.PROPERTY_MODERATE
    serializer_class = PropertyManagementSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        property_obj = get_object_or_404(
            managed_properties(request.user).select_for_update(),
            pk=kwargs['pk'],
        )
        self.check_object_permissions(request, property_obj)
        publication_status = request.data.get('publication_status')
        if publication_status not in (
            Property.PublicationStatus.PUBLISHED,
            Property.PublicationStatus.DRAFT,
        ):
            raise ValidationError({
                'publication_status': 'Choose published or draft.'
            })
        if (
            publication_status == Property.PublicationStatus.PUBLISHED
            and property_obj.status not in (Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE)
        ):
            raise ValidationError({
                'publication_status': 'Only available properties can be published.'
            })
        old_status = property_obj.publication_status
        property_obj.publication_status = publication_status
        if publication_status == Property.PublicationStatus.PUBLISHED:
            property_obj.moderation_note = ''
        property_obj.save(update_fields=['publication_status', 'moderation_note', 'updated_at'])
        if old_status != publication_status:
            record_admin_action(
                request.user,
                action='property_publication_changed',
                object_type='property',
                object_id=property_obj.pk,
                changes={'publication_status': {'from': old_status, 'to': publication_status}},
            )
        return Response(self.get_serializer(property_obj).data)


class ManagedPropertyImageListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsListingManager]
    serializer_class = PropertyImageManagementSerializer
    queryset = PropertyImage.objects.none()

    def get_property_queryset(self):
        return editable_properties(self.request.user)

    def get_queryset(self):
        return PropertyImage.objects.filter(
            property__in=self.get_property_queryset(),
            property_id=self.kwargs['property_id'],
        ).select_related('property')

    @transaction.atomic
    def perform_create(self, serializer):
        managed_property = get_object_or_404(
            self.get_property_queryset(),
            pk=self.kwargs['property_id'],
        )
        property_obj = get_object_or_404(
            Property.objects.select_for_update(),
            pk=managed_property.pk,
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
            property__in=editable_properties(self.request.user),
            property_id=self.kwargs['property_id'],
        ).select_related('property')

    @transaction.atomic
    def perform_update(self, serializer):
        image = self.get_object()
        managed_property = get_object_or_404(
            editable_properties(self.request.user),
            pk=self.kwargs['property_id'],
        )
        property_obj = get_object_or_404(
            Property.objects.select_for_update(),
            pk=managed_property.pk,
        )
        if serializer.validated_data.get('is_primary', image.is_primary):
            property_obj.images.exclude(pk=image.pk).update(is_primary=False)
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        property_obj = get_object_or_404(
            Property.objects.select_for_update(),
            pk=instance.property_id,
        )
        instance.image.delete(save=False)
        instance.delete()
