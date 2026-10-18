from copy import copy
from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from django.utils.text import slugify
from django.db import transaction
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from accounts.models import Profile
from properties.access import can_access_property_image_original
from properties.models import Amenity, Location, Property, PropertyAgentAssignment, PropertyImage
from properties.search_terms import normalize_search_text


class BulkDeleteIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=100,
    )

    def validate_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Each listing can only be selected once.')
        return value


class LocationSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(read_only=True, allow_null=True)
    city_id = serializers.SerializerMethodField()
    slug = serializers.SlugField(required=False, allow_blank=True, max_length=140)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Location
        fields = [
            'id', 'name', 'name_am', 'aliases_en', 'aliases_am', 'slug', 'location_type', 'parent_id',
            'city_id', 'parent',
            'is_active', 'display_order',
        ]
        read_only_fields = ['id', 'parent_id']
        validators = []

    aliases_en = serializers.ListField(
        child=serializers.CharField(max_length=120, allow_blank=False, trim_whitespace=True),
        required=False,
        allow_empty=True,
        max_length=20,
    )
    aliases_am = serializers.ListField(
        child=serializers.CharField(max_length=120, allow_blank=False, trim_whitespace=True),
        required=False,
        allow_empty=True,
        max_length=20,
    )

    def validate_parent(self, value):
        if value is not None and not value.is_active:
            raise serializers.ValidationError('An active location must have an active parent.')
        ancestor = value
        while ancestor is not None:
            if self.instance is not None and ancestor.pk == self.instance.pk:
                raise serializers.ValidationError('A location cannot be placed beneath itself or one of its descendants.')
            ancestor = ancestor.parent
        return value

    def to_internal_value(self, data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        profile = Profile.objects.filter(user=user).select_related('assigned_city').first() if (
            user and user.is_authenticated
        ) else None
        is_admin = bool(user and user.is_superuser) or bool(
            profile and profile.role == Profile.Role.ADMINISTRATOR
        )
        is_agent = not is_admin and bool(profile and profile.role == Profile.Role.AGENT)
        if not (is_admin or is_agent):
            return super().to_internal_value(data)

        if isinstance(data, dict):
            editable_fields = {'name', 'name_am', 'is_active', 'display_order'}
            if is_admin and self.instance is None:
                editable_fields.update({'location_type', 'parent'})
            unsupported_fields = set(data) - editable_fields
            if unsupported_fields:
                raise serializers.ValidationError({
                    field: ['This field is fixed or is not editable here.']
                    for field in sorted(unsupported_fields)
                })
            data = data.copy()
            if is_agent:
                if profile.assigned_city_id is None:
                    raise serializers.ValidationError({
                        'parent': 'Ask an administrator to assign a city before managing sub-cities.',
                    })
                data['location_type'] = Location.Type.SUBCITY
                data['parent'] = profile.assigned_city_id
            elif self.instance is not None:
                if self.instance.location_type not in (Location.Type.CITY, Location.Type.SUBCITY):
                    raise serializers.ValidationError({
                        'location_type': 'Administrators can manage marketplace cities and sub-cities only.',
                    })
                data['location_type'] = self.instance.location_type
                data['parent'] = self.instance.parent_id
            else:
                location_type = data.get('location_type', Location.Type.CITY)
                if location_type not in (Location.Type.CITY, Location.Type.SUBCITY):
                    raise serializers.ValidationError({
                        'location_type': 'Administrators can create marketplace cities or sub-cities only.',
                    })
                data['location_type'] = location_type
                if location_type == Location.Type.CITY:
                    country = Location.objects.filter(
                        location_type=Location.Type.COUNTRY,
                        name__iexact='Ethiopia',
                        is_active=True,
                    ).first()
                    if country is None:
                        raise serializers.ValidationError({
                            'parent': 'An active Ethiopia country location is required before adding a city.',
                        })
                    if data.get('parent') is not None and str(data['parent']) != str(country.pk):
                        raise serializers.ValidationError({
                            'parent': 'Marketplace cities must be placed directly under Ethiopia.',
                        })
                    data['parent'] = country.pk
                elif data.get('parent') is None:
                    raise serializers.ValidationError({
                        'parent': 'Choose a city or city administration for this sub-city.',
                    })
        return super().to_internal_value(data)

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_city_id(self, obj):
        current = obj
        while current is not None:
            if current.location_type in (Location.Type.CITY, Location.Type.CITY_ADMINISTRATION):
                return current.pk
            current = current.parent
        return None

    def validate_aliases_en(self, value):
        return self._normalize_aliases(value)

    def validate_aliases_am(self, value):
        return self._normalize_aliases(value)

    @staticmethod
    def _normalize_aliases(value):
        aliases = []
        for alias in value:
            normalized = normalize_search_text(alias)
            if normalized and normalized not in aliases:
                aliases.append(normalized)
        return aliases

    def validate(self, attrs):
        location = copy(self.instance) if self.instance is not None else Location()
        for field, value in attrs.items():
            setattr(location, field, value)
        if (
            self.instance is not None
            and self.instance.is_active
            and attrs.get('is_active') is False
            and _location_has_active_descendants(self.instance)
        ):
            raise serializers.ValidationError({
                'is_active': 'Deactivate active descendant locations before deactivating this location.',
            })
        if location.is_active:
            ancestor = location.parent
            while ancestor is not None:
                if not ancestor.is_active:
                    raise serializers.ValidationError({
                        'is_active': 'Every parent location must be active for this location to be active.',
                    })
                ancestor = ancestor.parent
        if (
            self.instance is not None
            and 'parent' in attrs
            and attrs['parent'] != self.instance.parent
            and _location_subtree_has_properties(self.instance)
        ):
            raise serializers.ValidationError({
                'parent': 'This location or its descendants are used by property records; reassign them before changing the hierarchy.',
            })

        candidate_slug = (attrs.get('slug') or getattr(location, 'slug', None) or '').strip()
        if not candidate_slug:
            candidate_slug = slugify(location.name)
        candidate_parent = attrs.get('parent', getattr(location, 'parent', None))

        request = self.context.get('request')
        user = getattr(request, 'user', None)
        profile = Profile.objects.filter(user=user).select_related('assigned_city').first() if (
            user and user.is_authenticated
        ) else None
        if profile and profile.role == Profile.Role.AGENT:
            if location.location_type != Location.Type.SUBCITY:
                raise serializers.ValidationError({
                    'location_type': 'Agents can manage sub-cities within their assigned city only.',
                })
            if candidate_parent is None or candidate_parent.pk != profile.assigned_city_id:
                raise serializers.ValidationError({
                    'parent': 'Choose your assigned city as the parent of this sub-city.',
                })
        elif (user and user.is_superuser) or (
            profile and profile.role == Profile.Role.ADMINISTRATOR
        ):
            if location.location_type not in (Location.Type.CITY, Location.Type.SUBCITY):
                raise serializers.ValidationError({
                    'location_type': 'Administrators can manage marketplace cities and sub-cities only.',
                })

        query = Location.objects.filter(slug=candidate_slug)
        if self.instance is not None:
            query = query.exclude(pk=self.instance.pk)
        if candidate_parent is None:
            if query.filter(parent__isnull=True).exists():
                raise serializers.ValidationError({'slug': 'A root location with this slug already exists.'})
        else:
            if query.filter(parent=candidate_parent).exists():
                raise serializers.ValidationError({'slug': 'A location with this slug already exists beneath the selected parent.'})

        location.slug = candidate_slug
        attrs['slug'] = candidate_slug
        if candidate_parent is not None and 'parent' not in attrs:
            attrs['parent'] = candidate_parent
        try:
            location.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict if hasattr(error, 'message_dict') else error.messages) from error
        return attrs


def _location_subtree_has_properties(location):
    frontier = {location.pk}
    visited = set()
    while frontier:
        visited.update(frontier)
        if Property.objects.filter(administrative_location_id__in=frontier).exists():
            return True
        frontier = set(
            Location.objects.filter(parent_id__in=frontier)
            .exclude(pk__in=visited)
            .values_list('pk', flat=True)
        )
    return False


def _location_has_active_descendants(location):
    frontier = set(location.children.values_list('pk', flat=True))
    visited = set()
    while frontier:
        if Location.objects.filter(pk__in=frontier, is_active=True).exists():
            return True
        visited.update(frontier)
        frontier = set(
            Location.objects.filter(parent_id__in=frontier)
            .exclude(pk__in=visited)
            .values_list('pk', flat=True)
        )
    return False


def _location_path(location):
    path = []
    current = location
    while current is not None:
        path.append({
            'id': current.pk,
            'name': current.name,
            'name_am': current.name_am,
            'location_type': current.location_type,
        })
        current = current.parent
    return list(reversed(path))


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'name_am', 'slug']


class PropertyTypeOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class PropertyImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ['id', 'url', 'caption', 'is_primary']

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_url(self, obj):
        if not obj.image:
            return None
        image_url = obj.image.url
        request = self.context.get('request')
        return request.build_absolute_uri(image_url) if request else image_url


class PublicPropertyListSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='property_type', read_only=True)
    currency = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    images = PropertyImageSerializer(many=True, read_only=True)
    location_name = serializers.SerializerMethodField()
    location_path = serializers.SerializerMethodField()
    service_type = serializers.CharField(read_only=True)
    public_contact_name = serializers.SerializerMethodField()
    public_contact_phone = serializers.SerializerMethodField()
    public_contact_email = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id',
            'title',
            'slug',
            'location',
            'administrative_location',
            'location_name',
            'location_path',
            'category',
            'listing_type',
            'price',
            'currency',
            'bedrooms',
            'bathrooms',
            'area_sqft',
            'area_value',
            'area_unit',
            'rental_frequency',
            'status',
            'service_type',
            'public_contact_name',
            'public_contact_phone',
            'public_contact_email',
            'primary_image',
            'images',
            'created_at',
        ]

    @extend_schema_field(serializers.CharField())
    def get_currency(self, obj):
        return 'ETB'

    @extend_schema_field(serializers.CharField())
    def get_status(self, obj):
        if obj.status == Property.Status.LEGACY_ACTIVE:
            return Property.Status.AVAILABLE
        return obj.status

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_location_name(self, obj):
        return obj.administrative_location.name if obj.administrative_location_id else ''

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_location_path(self, obj):
        return _location_path(obj.administrative_location) if obj.administrative_location_id else []

    def _public_agent_managed_listing(self, obj):
        agent = obj.submitted_by
        if (
            obj.service_type != Property.ServiceType.AGENT_MANAGED
            or agent is None
            or not agent.is_active
        ):
            return False
        profile = getattr(agent, 'profile', None)
        return (
            profile is not None
            and profile.role == Profile.Role.AGENT
            and profile.agent_approved
            and any(assignment.agent_id == agent.pk for assignment in obj.agent_assignments.all())
        )

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_public_contact_name(self, obj):
        return ''

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_public_contact_phone(self, obj):
        if obj.service_type == Property.ServiceType.OWNER_ANNOUNCED:
            announcement = getattr(obj, 'owner_announcement', None)
            if announcement is not None:
                return announcement.owner_contact_phone
        return obj.contact_phone

    @extend_schema_field(serializers.EmailField(allow_blank=True))
    def get_public_contact_email(self, obj):
        if self._public_agent_managed_listing(obj):
            return obj.contact_email
        return ''

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj):
        image = next((item for item in obj.images.all() if item.is_primary), None)
        if image is None:
            image = next(iter(obj.images.all()), None)
        if image is None or not image.image:
            return None
        image_url = image.image.url
        request = self.context.get('request')
        return request.build_absolute_uri(image_url) if request else image_url


class PublicPropertyDetailSerializer(PublicPropertyListSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)
    images = PropertyImageSerializer(many=True, read_only=True)

    class Meta(PublicPropertyListSerializer.Meta):
        fields = PublicPropertyListSerializer.Meta.fields + [
            'description',
            'features',
            'amenities',
            'updated_at',
        ]


class PropertyManagementSerializer(serializers.ModelSerializer):
    requires_listing_contact_phone = True

    administrative_location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        required=False,
        allow_null=True,
    )
    location_path = serializers.SerializerMethodField()
    category = serializers.ChoiceField(source='property_type', choices=Property.PROPERTY_TYPES)
    listing_type = serializers.ChoiceField(choices=Property.ListingType.choices)
    status = serializers.ChoiceField(
        choices=[
            (Property.Status.AVAILABLE, 'Available'),
            (Property.Status.RENTED, 'Rented'),
            (Property.Status.SOLD, 'Sold'),
            (Property.Status.INACTIVE, 'Inactive'),
        ],
        required=False,
        default=Property.Status.AVAILABLE,
    )
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    area_value = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=False,
        allow_null=True,
    )
    area_unit = serializers.ChoiceField(
        choices=Property.AreaUnit.choices,
        required=False,
        allow_blank=True,
    )
    rental_frequency = serializers.ChoiceField(
        choices=Property.RentalFrequency.choices,
        required=False,
        allow_blank=True,
    )
    amenities = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Amenity.objects.all(),
        required=False,
    )
    images = PropertyImageSerializer(many=True, read_only=True)
    currency = serializers.SerializerMethodField()
    publication_status = serializers.ChoiceField(
        choices=Property.PublicationStatus.choices,
        read_only=True,
    )
    submitted_by_id = serializers.IntegerField(read_only=True, allow_null=True)
    moderation_note = serializers.CharField(read_only=True)

    class Meta:
        model = Property
        fields = [
            'id',
            'title',
            'slug',
            'location',
            'administrative_location',
            'location_path',
            'category',
            'listing_type',
            'price',
            'currency',
            'bedrooms',
            'bathrooms',
            'area_sqft',
            'area_value',
            'area_unit',
            'rental_frequency',
            'description',
            'features',
            'status',
            'publication_status',
            'is_featured',
            'submitted_by_id',
            'moderation_note',
            'amenities',
            'images',
            'contact_name',
            'contact_phone',
            'contact_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'slug',
            'publication_status',
            'is_featured',
            'submitted_by_id',
            'moderation_note',
            'created_at',
            'updated_at',
        ]

    @extend_schema_field(serializers.CharField())
    def get_currency(self, obj):
        return 'ETB'

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_location_path(self, obj):
        return _location_path(obj.administrative_location) if obj.administrative_location_id else []

    def to_internal_value(self, data):
        unsupported = {'latitude', 'longitude', 'exact_location_is_public'}.intersection(data.keys())
        if unsupported:
            raise serializers.ValidationError({
                field: 'GPS/map location is no longer supported.'
                for field in unsupported
            })
        return super().to_internal_value(data)

    def validate(self, attrs):
        listing_type = attrs.get(
            'listing_type',
            self.instance.listing_type if self.instance else Property.ListingType.SALE,
        )
        if self.instance is None and self.requires_listing_contact_phone:
            contact_phone = (attrs.get('contact_phone') or '').strip()
            if not contact_phone:
                request = self.context.get('request')
                user = getattr(request, 'user', None)
                agent_profile = Profile.objects.filter(
                    user=user,
                    role=Profile.Role.AGENT,
                    agent_approved=True,
                ).first() if user and user.is_authenticated else None
                contact_phone = (agent_profile.phone if agent_profile else '').strip()
            if not contact_phone:
                raise serializers.ValidationError({
                    'contact_phone': 'A phone number is required when registering a property.',
                })
            attrs['contact_phone'] = contact_phone
        status = attrs.get('status', self.instance.status if self.instance else Property.Status.AVAILABLE)
        if status == Property.Status.RENTED and listing_type != Property.ListingType.RENT:
            raise serializers.ValidationError({'status': 'Only rental listings can be marked rented.'})
        if status == Property.Status.SOLD and listing_type != Property.ListingType.SALE:
            raise serializers.ValidationError({'status': 'Only sale listings can be marked sold.'})
        area_value = attrs.get('area_value', self.instance.area_value if self.instance else None)
        area_unit = attrs.get('area_unit', self.instance.area_unit if self.instance else '')
        if (area_value is None) != (not area_unit):
            raise serializers.ValidationError(
                {'area_unit': 'Provide a supported measurement unit together with the property size.'}
            )
        rental_frequency = attrs.get(
            'rental_frequency',
            self.instance.rental_frequency if self.instance else '',
        )
        if listing_type == Property.ListingType.RENT:
            became_rental = self.instance is None or self.instance.listing_type != Property.ListingType.RENT
            frequency_changed = 'rental_frequency' in attrs
            if not rental_frequency and (became_rental or frequency_changed):
                raise serializers.ValidationError(
                    {'rental_frequency': 'Choose a rental period for rental listings.'}
                )
            if rental_frequency == Property.RentalFrequency.WEEKLY and (
                self.instance is None or self.instance.rental_frequency != Property.RentalFrequency.WEEKLY
            ):
                raise serializers.ValidationError(
                    {'rental_frequency': 'New rental listings must use daily, monthly, or yearly pricing.'}
                )
        if listing_type == Property.ListingType.SALE and rental_frequency:
            raise serializers.ValidationError(
                {'rental_frequency': 'Rental frequency can only be set for rental listings.'}
            )
        location_submitted = 'administrative_location' in attrs
        administrative_location = attrs.get(
            'administrative_location',
            self.instance.administrative_location if self.instance else None,
        )
        if (self.instance is None or location_submitted) and administrative_location is None:
            raise serializers.ValidationError({
                'administrative_location': 'Select a configured city or town and its applicable area.',
            })
        if administrative_location is not None:
            location_is_unchanged = (
                self.instance is not None
                and administrative_location.pk == self.instance.administrative_location_id
            )
            path = []
            current = administrative_location
            while current is not None:
                path.append(current)
                current = current.parent
            if not administrative_location.is_active and not location_is_unchanged:
                raise serializers.ValidationError({
                    'administrative_location': 'Choose an active location for a new or changed listing.',
                })
            if not location_is_unchanged:
                if any(not item.is_active for item in path):
                    raise serializers.ValidationError({
                        'administrative_location': 'Every level in the selected location path must be active.',
                    })
                if not any(
                    item.location_type in (Location.Type.CITY, Location.Type.CITY_ADMINISTRATION)
                    for item in path
                ):
                    raise serializers.ValidationError({
                        'administrative_location': 'Select a city or town in the location hierarchy.',
                    })
                if (
                    any(item.location_type == Location.Type.CITY_ADMINISTRATION for item in path)
                    and not any(item.location_type == Location.Type.SUBCITY for item in path)
                ):
                    raise serializers.ValidationError({
                        'administrative_location': 'Select a configured sub-city / Kifle Ketema for this city administration.',
                    })
            request = self.context.get('request')
            user = getattr(request, 'user', None)
            agent_profile = Profile.objects.filter(
                user=user,
                role=Profile.Role.AGENT,
                agent_approved=True,
            ).first() if user and user.is_authenticated else None
            if agent_profile:
                location_city_id = next(
                    (
                        item.pk for item in path
                        if item.location_type == Location.Type.CITY
                    ),
                    None,
                )
                if (
                    agent_profile.assigned_city_id is None
                    or location_city_id != agent_profile.assigned_city_id
                    or (
                        not location_is_unchanged
                        and administrative_location.location_type != Location.Type.SUBCITY
                    )
                ):
                    raise serializers.ValidationError({
                        'administrative_location': 'Choose a sub-city within your assigned city.',
                    })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        amenities = validated_data.pop('amenities', [])
        user = self.context['request'].user
        agent_profile = Profile.objects.filter(
            user=user,
            role=Profile.Role.AGENT,
            agent_approved=True,
        ).first()
        if agent_profile:
            if not validated_data.get('contact_phone'):
                validated_data['contact_phone'] = agent_profile.phone
            if not validated_data.get('contact_email'):
                validated_data['contact_email'] = user.email
        if 'area_sqft' in validated_data and 'area_value' not in validated_data:
            area_sqft = validated_data['area_sqft']
            validated_data['area_value'] = Decimal(area_sqft) if area_sqft > 0 else None
            validated_data['area_unit'] = Property.AreaUnit.SQUARE_FEET if area_sqft > 0 else ''
        property_obj = Property.objects.create(
            owner=None,
            submitted_by=user,
            publication_status=Property.PublicationStatus.PUBLISHED,
            **validated_data,
        )
        if agent_profile:
            PropertyAgentAssignment.objects.create(property=property_obj, agent=user)
        property_obj.amenities.set(amenities)
        return property_obj

    @transaction.atomic
    def update(self, instance, validated_data):
        amenities = validated_data.pop('amenities', None)
        if 'area_sqft' in validated_data and 'area_value' not in validated_data:
            area_sqft = validated_data['area_sqft']
            validated_data['area_value'] = Decimal(area_sqft) if area_sqft > 0 else None
            validated_data['area_unit'] = Property.AreaUnit.SQUARE_FEET if area_sqft > 0 else ''
        property_obj = super().update(instance, validated_data)
        if amenities is not None:
            property_obj.amenities.set(amenities)
        return property_obj


class PropertyImageManagementSerializer(serializers.ModelSerializer):
    MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
    original_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'original_url', 'caption', 'is_primary', 'created_at']
        read_only_fields = ['id', 'original_url', 'created_at']

    def get_original_url(self, obj) -> str | None:
        request = self.context.get('request')
        if (
            not obj.original_image
            or request is None
            or not can_access_property_image_original(request.user, obj.property)
        ):
            return None
        return request.build_absolute_uri(
            reverse('api:property-image-original', kwargs={'pk': obj.pk}),
        )

    def validate_image(self, value):
        if value.size > self.MAX_IMAGE_SIZE_BYTES:
            raise serializers.ValidationError('Image files must be 10 MB or smaller.')
        return value
