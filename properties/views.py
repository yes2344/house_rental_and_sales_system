from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import filters, generics
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    HasManagementPermission,
    IsAuthenticatedPropertyManagerOrAdministrator,
    IsLocationManager,
    IsListingManager,
    has_management_permission,
    has_listing_role,
)
from accounts.models import Profile
from admin.audit import record_admin_action
from properties.access import (
    can_access_property_image_original,
    editable_properties,
    managed_properties,
    public_properties,
)
from properties.access import agent_city_location_ids
from properties.filters import PublicPropertyFilter, PublicPropertyOrderingFilter
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
    PropertyTypeOptionSerializer,
    BulkDeleteIdsSerializer,
)


PUBLIC_STATUSES = [Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE]


class IsManagedPropertyDeleter(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        user = request.user
        can_delete_all = any(
            has_management_permission(user, permission)
            for permission in (
                Profile.Permission.PROPERTY_DELETE_ALL,
                Profile.Permission.PROPERTY_EDIT_ALL,
            )
        )
        can_delete_own = (
            has_listing_role(user, Profile.Role.AGENT, agent_approved=True)
            and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
        )
        return can_delete_all or can_delete_own


class PublicAmenityListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AmenitySerializer
    queryset = Amenity.objects.all().order_by('name')

    @extend_schema(summary='List amenities available for property listings')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicPropertyTypeListView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PropertyTypeOptionSerializer

    @extend_schema(summary='List property types available for marketplace listings')
    def get(self, request, *args, **kwargs):
        data = [
            {'value': value, 'label': label}
            for value, label in Property.PROPERTY_TYPES
        ]
        return Response(self.get_serializer(data, many=True).data)


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
                .select_related(
                    'parent',
                    'parent__parent',
                    'parent__parent__parent',
                    'parent__parent__parent__parent',
                    'parent__parent__parent__parent__parent',
                )
                .order_by('display_order', 'name')[:20]
            )
        if self.request.query_params.get('all') == '1':
            return queryset.select_related(
                'parent',
                'parent__parent',
                'parent__parent__parent',
                'parent__parent__parent__parent',
                'parent__parent__parent__parent__parent',
            ).order_by('display_order', 'name')
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            if not Location.objects.filter(pk=parent_id, is_active=True).exists():
                return queryset.none()
            queryset = queryset.filter(parent_id=parent_id)
        location_types = self.request.query_params.get('types')
        location_type = self.request.query_params.get('type')
        if location_types or location_type:
            values = [
                value.strip()
                for value in (location_types or location_type or '').split(',')
                if value.strip()
            ]
            queryset = queryset.filter(location_type__in=values)
        elif not parent_id:
            queryset = queryset.filter(parent__isnull=True)
        return queryset.select_related(
            'parent',
            'parent__parent',
            'parent__parent__parent',
            'parent__parent__parent__parent',
            'parent__parent__parent__parent__parent',
        ).order_by('display_order', 'name')


class ManagedLocationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsLocationManager]
    serializer_class = LocationSerializer
    pagination_class = None
    queryset = Location.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset
        queryset = Location.objects.all()
        profile = Profile.objects.filter(user=self.request.user).select_related('assigned_city').first()
        if not self.request.user.is_superuser and profile and profile.role == Profile.Role.AGENT:
            queryset = queryset.filter(pk__in=agent_city_location_ids(self.request.user))
        if self.request.query_params.get('all') == '1':
            return queryset.select_related(
                'parent',
                'parent__parent',
                'parent__parent__parent',
                'parent__parent__parent__parent',
                'parent__parent__parent__parent__parent',
            ).order_by('display_order', 'name', 'pk')
        parent_id = self.request.query_params.get('parent_id')
        return queryset.filter(parent_id=parent_id) if parent_id else queryset.filter(parent__isnull=True)

    def perform_create(self, serializer):
        location = serializer.save()
        record_admin_action(
            self.request.user,
            action='location_created',
            object_type='location',
            object_id=location.pk,
            changes={
                'name': location.name,
                'name_am': location.name_am,
                'location_type': location.location_type,
                'parent_id': location.parent_id,
                'is_active': location.is_active,
                'display_order': location.display_order,
            },
        )


class ManagedLocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsLocationManager]
    serializer_class = LocationSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        queryset = Location.objects.all()
        profile = Profile.objects.filter(user=self.request.user).select_related('assigned_city').first()
        if not self.request.user.is_superuser and profile and profile.role == Profile.Role.AGENT:
            queryset = queryset.filter(pk__in=agent_city_location_ids(self.request.user))
            queryset = queryset.filter(location_type=Location.Type.SUBCITY)
        elif self.request.user.is_superuser or (
            profile and profile.role == Profile.Role.ADMINISTRATOR
        ):
            queryset = queryset.filter(location_type=Location.Type.CITY)
        return queryset

    def perform_update(self, serializer):
        instance = serializer.instance
        before = {
            'name': instance.name,
            'name_am': instance.name_am,
            'location_type': instance.location_type,
            'parent_id': instance.parent_id,
            'is_active': instance.is_active,
            'display_order': instance.display_order,
            'aliases_en': instance.aliases_en,
            'aliases_am': instance.aliases_am,
        }
        location = serializer.save()
        after = {
            'name': location.name,
            'name_am': location.name_am,
            'location_type': location.location_type,
            'parent_id': location.parent_id,
            'is_active': location.is_active,
            'display_order': location.display_order,
            'aliases_en': location.aliases_en,
            'aliases_am': location.aliases_am,
        }
        changes = {
            key: {'from': before[key], 'to': after[key]}
            for key in before
            if before[key] != after[key]
        }
        if changes:
            record_admin_action(
                self.request.user,
                action='location_updated',
                object_type='location',
                object_id=location.pk,
                changes=changes,
            )

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.children.exists():
            raise ValidationError({
                'detail': 'Remove or reassign child locations before deleting this location.',
            })
        if Property.objects.filter(administrative_location_id=instance.pk).exists():
            raise ValidationError({
                'detail': 'This location is used by property listings. Deactivate it instead of deleting it.',
            })
        if Profile.objects.filter(assigned_city=instance).exists():
            raise ValidationError({
                'detail': 'This city is assigned to agents. Reassign those agents before deleting it.',
            })
        record_admin_action(
            self.request.user,
            action='location_deleted',
            object_type='location',
            object_id=instance.pk,
            changes={
                'name': instance.name,
                'location_type': instance.location_type,
                'parent_id': instance.parent_id,
            },
        )
        instance.delete()


class PublicPropertyListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicPropertyListSerializer
    filter_backends = [DjangoFilterBackend, BilingualPropertySearchFilter, PublicPropertyOrderingFilter]
    filterset_class = PublicPropertyFilter
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            public_properties()
            .select_related('submitted_by')
            .prefetch_related(
                'images',
                'amenities',
                'agent_assignments__agent__profile',
            )
            .select_related(
                'administrative_location',
                'administrative_location__parent',
                'administrative_location__parent__parent',
                'administrative_location__parent__parent__parent',
                'administrative_location__parent__parent__parent__parent',
                'administrative_location__parent__parent__parent__parent__parent',
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
            'amenity slugs. `ordering` accepts only `-created_at`, `created_at`, `-price`, or `price`. '
            'Price sorting groups sale listings first, followed by daily, weekly, monthly, then yearly '
            'rentals; numeric ETB prices are sorted within each group without converting rental periods. '
            'Public results always exclude unpublished, rented, sold, and inactive listings.'
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
        'agent_assignments__agent__profile',
    ).select_related(
        'administrative_location',
        'administrative_location__parent',
        'administrative_location__parent__parent',
        'administrative_location__parent__parent__parent',
        'administrative_location__parent__parent__parent__parent',
        'administrative_location__parent__parent__parent__parent__parent',
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
            .select_related(
                'owner',
                'administrative_location',
                'administrative_location__parent',
                'administrative_location__parent__parent',
                'administrative_location__parent__parent__parent',
                'administrative_location__parent__parent__parent__parent',
                'administrative_location__parent__parent__parent__parent__parent',
            )
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


class ManagedPropertyBulkDeleteView(APIView):
    permission_classes = [IsManagedPropertyDeleter]
    serializer_class = BulkDeleteIdsSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['ids']
        properties = list(
            managed_properties(request.user)
            .select_for_update()
            .filter(pk__in=ids)
            .order_by('pk')
        )
        if {property_obj.pk for property_obj in properties} != set(ids):
            raise NotFound('One or more selected listings are unavailable.')

        for property_obj in properties:
            record_admin_action(
                request.user,
                action='property_deleted',
                object_type='property',
                object_id=property_obj.pk,
                changes={
                    'title': property_obj.title,
                    'service_type': property_obj.service_type,
                },
            )
            property_obj.delete()

        return Response({'deleted_count': len(properties)})


class ManagedPropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedPropertyManagerOrAdministrator]
    serializer_class = PropertyManagementSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return (
            managed_properties(self.request.user)
            .select_related(
                'owner',
                'administrative_location',
                'administrative_location__parent',
                'administrative_location__parent__parent',
                'administrative_location__parent__parent__parent',
                'administrative_location__parent__parent__parent__parent',
                'administrative_location__parent__parent__parent__parent__parent',
            )
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
        instance.delete()


class PropertyImageOriginalView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyImageManagementSerializer
    queryset = PropertyImage.objects.none()

    @extend_schema(responses={200: OpenApiTypes.BINARY})
    def get(self, request, *args, **kwargs):
        image = get_object_or_404(
            PropertyImage.objects.select_related(
                'property',
                'property__owner_announcement',
            ),
            pk=kwargs['pk'],
        )
        if not can_access_property_image_original(request.user, image.property):
            raise Http404
        if not image.original_image or not image.original_image.storage.exists(image.original_image.name):
            raise Http404

        response = FileResponse(
            image.original_image.open('rb'),
            content_type=image.original_content_type or 'application/octet-stream',
            as_attachment=False,
            filename=image.original_filename or 'property-image',
        )
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
