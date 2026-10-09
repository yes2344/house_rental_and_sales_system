from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from accounts.models import Profile
from properties.models import Amenity, Property, PropertyBrokerAssignment, PropertyImage


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

    class Meta:
        model = Property
        fields = [
            'id',
            'title',
            'slug',
            'location',
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
        if listing_type == Property.ListingType.SALE and rental_frequency:
            raise serializers.ValidationError(
                {'rental_frequency': 'Rental frequency can only be set for rental listings.'}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        amenities = validated_data.pop('amenities', [])
        user = self.context['request'].user
        if 'area_sqft' in validated_data and 'area_value' not in validated_data:
            area_sqft = validated_data['area_sqft']
            validated_data['area_value'] = Decimal(area_sqft) if area_sqft > 0 else None
            validated_data['area_unit'] = Property.AreaUnit.SQUARE_FEET if area_sqft > 0 else ''
        property_obj = Property.objects.create(
            owner=None,
            submitted_by=user,
            publication_status=Property.PublicationStatus.DRAFT,
            **validated_data,
        )
        if Profile.objects.filter(
            user=user,
            role=Profile.Role.BROKER,
            broker_approved=True,
        ).exists():
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
        if any(getattr(instance, field) != value for field, value in validated_data.items()):
            if instance.publication_status != Property.PublicationStatus.DRAFT:
                instance.publication_status = Property.PublicationStatus.DRAFT
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
