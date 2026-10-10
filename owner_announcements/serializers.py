from datetime import date
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from django.utils import timezone

from django.db import transaction
from rest_framework import serializers

from properties.models import Amenity, Location, Property, PropertyImage
from owner_announcements.models import (
    InAppNotification,
    OwnerAnnouncement,
    OwnerAnnouncementAgreement,
    OwnerAnnouncementEvent,
)


class AnnouncementImageListField(serializers.ListField):
    MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    child = serializers.ImageField()

    def get_value(self, dictionary):
        if hasattr(dictionary, 'getlist'):
            files = dictionary.getlist(self.field_name)
            if files:
                return files
        return super().get_value(dictionary)

    def validate(self, data):
        data = super().validate(data)
        for image in data:
            if image.size > self.MAX_IMAGE_SIZE_BYTES:
                raise serializers.ValidationError('Image files must be 10 MB or smaller.')
            if Path(image.name).suffix.lower() not in self.ALLOWED_EXTENSIONS:
                raise serializers.ValidationError('Use a JPG, PNG, or WebP image.')
        return data


class AnnouncementPropertySerializer(serializers.ModelSerializer):
    administrative_location_name = serializers.CharField(
        source='administrative_location.name',
        read_only=True,
        default='',
    )
    images = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id',
            'title',
            'slug',
            'location',
            'administrative_location',
            'administrative_location_name',
            'property_type',
            'listing_type',
            'price',
            'rental_frequency',
            'bedrooms',
            'bathrooms',
            'area_sqft',
            'area_value',
            'area_unit',
            'description',
            'features',
            'latitude',
            'longitude',
            'images',
        ]

    def get_images(self, obj):
        return [
            {
                'id': image.pk,
                'url': self.context['request'].build_absolute_uri(image.image.url) if image.image else None,
                'caption': image.caption,
                'is_primary': image.is_primary,
            }
            for image in obj.images.all()
        ]


class OwnerAnnouncementEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_username', read_only=True, default='')

    class Meta:
        model = OwnerAnnouncementEvent
        fields = ['event_type', 'from_status', 'to_status', 'details', 'actor_name', 'created_at']


class OwnerAnnouncementAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnerAnnouncementAgreement
        fields = [
            'start_date',
            'end_date',
            'duration_months',
            'terms',
            'renewal_conditions',
            'public_contact_visible',
            'status',
            'created_at',
        ]


class OwnerAnnouncementSerializer(serializers.ModelSerializer):
    property = AnnouncementPropertySerializer(read_only=True)
    agreements = OwnerAnnouncementAgreementSerializer(many=True, read_only=True)
    events = OwnerAnnouncementEventSerializer(many=True, read_only=True)

    class Meta:
        model = OwnerAnnouncement
        fields = [
            'id',
            'property',
            'status',
            'broker_feedback',
            'owner_contact_name',
            'owner_contact_phone',
            'owner_contact_email',
            'public_contact_name',
            'public_contact_phone',
            'public_contact_email',
            'public_contact_visible',
            'renewal_requested_at',
            'submitted_at',
            'reviewed_at',
            'agreements',
            'events',
        ]


class OwnerAnnouncementSubmissionSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    location = serializers.CharField(max_length=200)
    administrative_location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    property_type = serializers.ChoiceField(choices=Property.PROPERTY_TYPES)
    listing_type = serializers.ChoiceField(choices=Property.ListingType.choices)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    rental_frequency = serializers.ChoiceField(
        choices=Property.RentalFrequency.choices,
        required=False,
        allow_blank=True,
    )
    bedrooms = serializers.IntegerField(min_value=0, max_value=100, required=False, default=0)
    bathrooms = serializers.IntegerField(min_value=0, max_value=100, required=False, default=0)
    area_sqft = serializers.IntegerField(min_value=0, max_value=10000000, required=False, default=0)
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
    description = serializers.CharField(max_length=10000)
    features = serializers.CharField(max_length=5000, required=False, allow_blank=True, default='')
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=-90,
        max_value=90,
        required=False,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=-180,
        max_value=180,
        required=False,
        allow_null=True,
    )
    amenities = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        many=True,
        required=False,
    )
    owner_contact_name = serializers.CharField(max_length=200)
    owner_contact_phone = serializers.CharField(max_length=50)
    owner_contact_email = serializers.EmailField(required=False, allow_blank=True, default='')
    images = AnnouncementImageListField(required=False, allow_empty=True, max_length=10)
    authorization_confirmed = serializers.BooleanField()
    terms_accepted = serializers.BooleanField(write_only=True)

    def validate_images(self, images):
        if self.instance is not None and self.instance.property.images.count() + len(images) > 10:
            raise serializers.ValidationError('A property can have at most 10 images.')
        return images

    def validate(self, attrs):
        authorization_confirmed = attrs.get(
            'authorization_confirmed',
            self.instance.authorization_confirmed if self.instance else False,
        )
        if not authorization_confirmed:
            raise serializers.ValidationError({'authorization_confirmed': 'Confirm that you are authorized to advertise this property.'})
        if self.instance is None and not attrs.get('terms_accepted'):
            raise serializers.ValidationError({'terms_accepted': 'Accept the announcement terms to continue.'})
        effective_listing_type = attrs.get(
            'listing_type',
            self.instance.property.listing_type if self.instance else Property.ListingType.SALE,
        )
        effective_frequency = attrs.get(
            'rental_frequency',
            self.instance.property.rental_frequency if self.instance else '',
        )
        if effective_listing_type == Property.ListingType.RENT:
            if effective_frequency not in (
                Property.RentalFrequency.DAILY,
                Property.RentalFrequency.MONTHLY,
                Property.RentalFrequency.YEARLY,
            ):
                raise serializers.ValidationError({'rental_frequency': 'Choose daily, monthly, or yearly rent pricing.'})
        elif effective_frequency:
            raise serializers.ValidationError({'rental_frequency': 'Sale listings do not use a rental period.'})
        latitude = attrs.get('latitude', self.instance.property.latitude if self.instance else None)
        longitude = attrs.get('longitude', self.instance.property.longitude if self.instance else None)
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError({'latitude': 'Provide both coordinates, or leave both blank.'})
        area_value = attrs.get('area_value', self.instance.property.area_value if self.instance else None)
        area_unit = attrs.get('area_unit', self.instance.property.area_unit if self.instance else '')
        if (area_value is None) != (not area_unit):
            raise serializers.ValidationError({'area_unit': 'Provide a measurement unit together with the property size.'})
        if attrs.get('administrative_location') and not attrs['administrative_location'].is_active:
            raise serializers.ValidationError({'administrative_location': 'Choose an active location.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        images = validated_data.pop('images', [])
        amenities = validated_data.pop('amenities', [])
        terms_accepted = validated_data.pop('terms_accepted')
        owner_contact_name = validated_data.pop('owner_contact_name')
        owner_contact_phone = validated_data.pop('owner_contact_phone')
        owner_contact_email = validated_data.pop('owner_contact_email')
        validated_data.pop('authorization_confirmed')
        property_obj = Property.objects.create(
            owner=self.context['request'].user,
            submitted_by=self.context['request'].user,
            publication_status=Property.PublicationStatus.PENDING_REVIEW,
            service_type=Property.ServiceType.OWNER_ANNOUNCED,
            exact_location_is_public=False,
            **validated_data,
        )
        property_obj.amenities.set(amenities)
        for image in images:
            PropertyImage.objects.create(property=property_obj, image=image)
        announcement = OwnerAnnouncement.objects.create(
            property=property_obj,
            submitter=self.context['request'].user,
            owner_contact_name=owner_contact_name,
            owner_contact_phone=owner_contact_phone,
            owner_contact_email=owner_contact_email,
            authorization_confirmed=True,
            terms_accepted_at=timezone.now(),
        )
        return announcement

    @transaction.atomic
    def update(self, instance, validated_data):
        images = validated_data.pop('images', None)
        amenities = validated_data.pop('amenities', None)
        validated_data.pop('terms_accepted', None)
        authorized = validated_data.pop('authorization_confirmed', instance.authorization_confirmed)
        if not authorized:
            raise serializers.ValidationError({'authorization_confirmed': 'Confirm that you remain authorized to advertise this property.'})
        for field in ('owner_contact_name', 'owner_contact_phone', 'owner_contact_email'):
            if field in validated_data:
                setattr(instance, field, validated_data.pop(field))
        property_fields = {
            'title', 'location', 'administrative_location', 'property_type', 'listing_type',
            'price', 'rental_frequency', 'bedrooms', 'bathrooms', 'area_sqft', 'area_value',
            'area_unit', 'description', 'features', 'latitude', 'longitude',
        }
        for field in property_fields:
            if field in validated_data:
                setattr(instance.property, field, validated_data.pop(field))
        if validated_data:
            raise serializers.ValidationError({key: 'This field cannot be changed here.' for key in validated_data})
        instance.property.exact_location_is_public = False
        instance.property.publication_status = Property.PublicationStatus.PENDING_REVIEW
        instance.property.save()
        if amenities is not None:
            instance.property.amenities.set(amenities)
        if images:
            for image in images:
                PropertyImage.objects.create(property=instance.property, image=image)
        previous_status = instance.status
        instance.status = OwnerAnnouncement.Status.PENDING_REVIEW
        instance.broker_feedback = ''
        instance.reviewed_by = None
        instance.reviewed_at = None
        instance.renewal_requested_at = None
        instance.save()
        OwnerAnnouncementEvent.objects.create(
            announcement=instance,
            actor=self.context['request'].user,
            event_type=OwnerAnnouncementEvent.Type.EDITED,
            from_status=previous_status,
            to_status=instance.status,
            details={'public_listing_hidden_until_review': True},
        )
        return instance


class BrokerAnnouncementSerializer(OwnerAnnouncementSerializer):
    class Meta(OwnerAnnouncementSerializer.Meta):
        fields = OwnerAnnouncementSerializer.Meta.fields + [
            'authorization_confirmed',
            'terms_accepted_at',
            'reviewed_by_id',
            'created_at',
            'updated_at',
        ]


class BrokerAnnouncementDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=['approve', 'request_corrections', 'reject', 'suspend'],
    )
    feedback = serializers.CharField(max_length=4000, required=False, allow_blank=True, default='')
    confirm_summary = serializers.BooleanField(required=False, default=False)
    agreement_start_date = serializers.DateField(required=False)
    agreement_end_date = serializers.DateField(required=False)
    duration_months = serializers.IntegerField(min_value=1, max_value=120, required=False)
    agreement_terms = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    renewal_conditions = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    public_contact_visible = serializers.BooleanField(required=False, default=False)
    public_contact_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    public_contact_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    public_contact_email = serializers.EmailField(required=False, allow_blank=True)
    exact_location_is_public = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        action = attrs['action']
        if action in ('request_corrections', 'reject', 'suspend') and not attrs['feedback'].strip():
            raise serializers.ValidationError({'feedback': 'Provide a clear reason for this decision.'})
        if action == 'approve':
            required_fields = ('agreement_start_date', 'agreement_end_date', 'duration_months', 'agreement_terms')
            missing = [field for field in required_fields if not attrs.get(field)]
            if missing:
                raise serializers.ValidationError({field: 'This field is required to approve the announcement.' for field in missing})
            if not attrs['confirm_summary']:
                raise serializers.ValidationError({'confirm_summary': 'Confirm the agreement and public-contact summary before approval.'})
            if attrs['agreement_end_date'] < attrs['agreement_start_date']:
                raise serializers.ValidationError({'agreement_end_date': 'The expiry date must be on or after the agreement start date.'})
            start_date = attrs['agreement_start_date']
            month_index = start_date.month - 1 + attrs['duration_months']
            year = start_date.year + month_index // 12
            month = month_index % 12 + 1
            expiry_month_day = monthrange(year, month)[1]
            expected_end_date = date(year, month, min(start_date.day, expiry_month_day)) - timedelta(days=1)
            if attrs['agreement_end_date'] != expected_end_date:
                raise serializers.ValidationError({
                    'agreement_end_date': f'For this start date and duration, choose {expected_end_date.isoformat()}.',
                })
        return attrs


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ['id', 'notification_type', 'message', 'announcement_id', 'read_at', 'created_at']
