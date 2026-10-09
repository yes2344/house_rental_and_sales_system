from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import (
    IsActiveAuthenticated,
    IsAuthenticatedPropertyManagerOrAdministrator,
)
from admin.audit import record_admin_action
from properties.access import editable_properties, managed_properties
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


def return_property_to_draft(property_obj, actor):
    if property_obj.publication_status == Property.PublicationStatus.DRAFT:
        return
    previous_status = property_obj.publication_status
    property_obj.publication_status = Property.PublicationStatus.DRAFT
    property_obj.save(update_fields=['publication_status', 'updated_at'])
    record_admin_action(
        actor,
        action='property_changed',
        object_type='property',
        object_id=property_obj.pk,
        changes={
            'publication_status': {
                'from': previous_status,
                'to': Property.PublicationStatus.DRAFT,
            },
        },
    )


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
    permission_classes = [IsActiveAuthenticated]
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
            action='property_draft_created',
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
        before = {
            field: getattr(instance, field)
            for field in (
                'status',
                'listing_type',
                'publication_status',
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


class ManagedPropertySubmitView(generics.GenericAPIView):
    permission_classes = [IsAuthenticatedPropertyManagerOrAdministrator]
    serializer_class = PropertyManagementSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        managed_property = get_object_or_404(
            managed_properties(request.user),
            pk=kwargs['pk'],
        )
        property_obj = get_object_or_404(
            Property.objects.select_for_update(),
            pk=managed_property.pk,
        )
        self.check_object_permissions(request, property_obj)

        errors = {}
        if not property_obj.advertising_authorized:
            errors['advertising_authorized'] = 'Confirm that you are authorized to advertise this property.'
        if not property_obj.contact_name.strip():
            errors['contact_name'] = 'Enter the responsible property contact name.'
        if not property_obj.contact_phone.strip() and not property_obj.contact_email.strip():
            errors['contact_phone'] = 'Provide a phone number or email for the responsible contact.'
        if property_obj.listing_type == Property.ListingType.RENT and not property_obj.rental_frequency:
            errors['rental_frequency'] = 'Choose a rental price frequency.'
        if property_obj.status not in (Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE):
            errors['status'] = 'Only available properties can be submitted for review.'
        if errors:
            raise ValidationError(errors)

        if property_obj.publication_status not in (
            Property.PublicationStatus.DRAFT,
            Property.PublicationStatus.REJECTED,
        ):
            raise ValidationError(
                {'publication_status': 'Only a draft or rejected listing can be submitted.'}
            )

        old_status = property_obj.publication_status
        property_obj.publication_status = Property.PublicationStatus.PENDING_REVIEW
        property_obj.moderation_note = ''
        property_obj.save(update_fields=['publication_status', 'moderation_note', 'updated_at'])
        record_admin_action(
            request.user,
            action='property_submitted',
            object_type='property',
            object_id=property_obj.pk,
            changes={
                'publication_status': {
                    'from': old_status,
                    'to': Property.PublicationStatus.PENDING_REVIEW,
                },
            },
        )
        return Response(self.get_serializer(property_obj).data)


class ManagedPropertyImageListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsActiveAuthenticated]
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
        return_property_to_draft(property_obj, self.request.user)


class ManagedPropertyImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsActiveAuthenticated]
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
        return_property_to_draft(property_obj, self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance):
        property_obj = get_object_or_404(
            Property.objects.select_for_update(),
            pk=instance.property_id,
        )
        instance.image.delete(save=False)
        instance.delete()
        return_property_to_draft(property_obj, self.request.user)
