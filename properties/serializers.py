from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from accounts.models import Profile
from properties.models import Amenity, Location, Property, PropertyBrokerAssignment, PropertyImage
from properties.search_terms import normalize_search_text
from owner_announcements.models import OwnerAnnouncement, OwnerAnnouncementAgreement


class LocationSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(read_only=True, allow_null=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Location
        fields = [
            'id', 'name', 'name_am', 'aliases_en', 'aliases_am', 'slug', 'location_type', 'parent_id', 'parent',
            'is_active', 'display_order', 'latitude', 'longitude',
        ]
        extra_kwargs = {'slug': {'required': False}}
        read_only_fields = ['id', 'parent_id']

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
        return value

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
        location = self.instance or Location()
        for field, value in attrs.items():
            setattr(location, field, value)
        if not location.slug:
            location.slug = slugify(location.name)
        try:
            location.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict if hasattr(error, 'message_dict') else error.messages) from error
        return attrs


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'name_am', 'slug']


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
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()
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
            'latitude',
            'longitude',
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

    @extend_schema_field(serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True))
    def get_latitude(self, obj):
        return obj.latitude if obj.has_public_coordinates else None

    @extend_schema_field(serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True))
    def get_longitude(self, obj):
        return obj.longitude if obj.has_public_coordinates else None

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_location_name(self, obj):
        return obj.administrative_location.name if obj.administrative_location_id else ''

    def _public_announcement(self, obj):
        if obj.service_type != Property.ServiceType.OWNER_ANNOUNCED:
            return None
        try:
            announcement = obj.owner_announcement
        except OwnerAnnouncement.DoesNotExist:
            return None
        today = timezone.localdate()
        valid_agreement = any(
            agreement.status == OwnerAnnouncementAgreement.Status.ACTIVE
            and agreement.start_date <= today <= agreement.end_date
            and agreement.public_contact_visible
            for agreement in announcement.agreements.all()
        )
        return announcement if announcement.public_contact_visible and valid_agreement else None

    def _public_broker_managed_listing(self, obj):
        broker = obj.submitted_by
        if (
            obj.service_type != Property.ServiceType.BROKER_MANAGED
            or broker is None
            or not broker.is_active
        ):
            return False
        profile = getattr(broker, 'profile', None)
        return (
            profile is not None
            and profile.role == Profile.Role.BROKER
            and profile.broker_approved
            and any(assignment.broker_id == broker.pk for assignment in obj.broker_assignments.all())
        )

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_public_contact_name(self, obj):
        announcement = self._public_announcement(obj)
        return announcement.public_contact_name if announcement else ''

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_public_contact_phone(self, obj):
        if self._public_broker_managed_listing(obj):
            return obj.contact_phone
        announcement = self._public_announcement(obj)
        return announcement.public_contact_phone if announcement else ''

    @extend_schema_field(serializers.EmailField(allow_blank=True))
    def get_public_contact_email(self, obj):
        if self._public_broker_managed_listing(obj):
            return obj.contact_email
        announcement = self._public_announcement(obj)
        return announcement.public_contact_email if announcement else ''

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
    administrative_location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
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
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal('-90'),
        max_value=Decimal('90'),
        required=False,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal('-180'),
        max_value=Decimal('180'),
        required=False,
        allow_null=True,
    )
    amenities = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Amenity.objects.all(),
        required=False,
    )
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
            'latitude',
            'longitude',
            'exact_location_is_public',
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

    def validate(self, attrs):
        listing_type = attrs.get(
            'listing_type',
            self.instance.listing_type if self.instance else Property.ListingType.SALE,
        )
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
        latitude = attrs.get('latitude', self.instance.latitude if self.instance else None)
        longitude = attrs.get('longitude', self.instance.longitude if self.instance else None)
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {'latitude': 'Provide both latitude and longitude, or leave both empty.'}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        amenities = validated_data.pop('amenities', [])
        user = self.context['request'].user
        broker_profile = Profile.objects.filter(
            user=user,
            role=Profile.Role.BROKER,
            broker_approved=True,
        ).first()
        if broker_profile:
            if not validated_data.get('contact_phone'):
                validated_data['contact_phone'] = broker_profile.phone
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
        if broker_profile:
            PropertyBrokerAssignment.objects.create(property=property_obj, broker=user)
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

    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'caption', 'is_primary', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_image(self, value):
        if value.size > self.MAX_IMAGE_SIZE_BYTES:
            raise serializers.ValidationError('Image files must be 10 MB or smaller.')
        return value
