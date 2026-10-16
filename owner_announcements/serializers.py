from django.utils import timezone
from rest_framework import serializers

from owner_announcements.models import (
    InAppNotification,
    OwnerAnnouncement,
    OwnerAnnouncementEvent,
)
from properties.models import Property
from properties.serializers import PropertyManagementSerializer


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ['id', 'notification_type', 'message', 'announcement_id', 'read_at', 'created_at']


class OwnerAnnouncementEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.username', read_only=True, allow_null=True)

    class Meta:
        model = OwnerAnnouncementEvent
        fields = ['event_type', 'from_status', 'to_status', 'details', 'actor_name', 'created_at']


class OwnerPropertySubmissionSerializer(PropertyManagementSerializer):
    status = serializers.ChoiceField(choices=Property.Status.choices, read_only=True)
    contact_name = serializers.CharField(read_only=True)
    contact_phone = serializers.CharField(read_only=True)
    contact_email = serializers.EmailField(read_only=True)
    owner_contact_name = serializers.CharField(max_length=200, write_only=True, required=False)
    owner_contact_phone = serializers.CharField(max_length=50, write_only=True, required=False)
    owner_contact_email = serializers.EmailField(allow_blank=True, write_only=True, required=False)
    authorization_confirmed = serializers.BooleanField(write_only=True, required=False)
    terms_accepted = serializers.BooleanField(write_only=True, required=False)
    submission_status = serializers.SerializerMethodField()
    review_feedback = serializers.SerializerMethodField()
    submission_events = serializers.SerializerMethodField()

    class Meta(PropertyManagementSerializer.Meta):
        fields = PropertyManagementSerializer.Meta.fields + [
            'owner_contact_name',
            'owner_contact_phone',
            'owner_contact_email',
            'authorization_confirmed',
            'terms_accepted',
            'submission_status',
            'review_feedback',
            'submission_events',
        ]
        read_only_fields = PropertyManagementSerializer.Meta.read_only_fields + [
            'status',
            'contact_name',
            'contact_phone',
            'contact_email',
            'submission_status',
            'review_feedback',
            'submission_events',
        ]

    def to_internal_value(self, data):
        protected = {
            'status',
            'publication_status',
            'service_type',
            'owner',
            'submitted_by',
            'advertising_authorized',
            'contact_publicly_visible',
            'is_featured',
            'contact_name',
            'contact_phone',
            'contact_email',
        }.intersection(data.keys())
        if protected:
            raise serializers.ValidationError({
                field: 'This field is set by the platform and cannot be submitted here.'
                for field in sorted(protected)
            })
        return super().to_internal_value(data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        announcement = getattr(instance, 'owner_announcement', None)
        if announcement is not None:
            representation.update({
                'owner_contact_name': announcement.owner_contact_name,
                'owner_contact_phone': announcement.owner_contact_phone,
                'owner_contact_email': announcement.owner_contact_email,
            })
        return representation

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None:
            required_fields = (
                'owner_contact_name',
                'owner_contact_phone',
                'authorization_confirmed',
                'terms_accepted',
            )
            missing = [field for field in required_fields if field not in attrs]
            if missing:
                raise serializers.ValidationError({
                    field: 'This field is required.'
                    for field in missing
                })
            if not attrs['authorization_confirmed']:
                raise serializers.ValidationError({
                    'authorization_confirmed': 'Confirm that you are authorized to advertise this property.'
                })
            if not attrs['terms_accepted']:
                raise serializers.ValidationError({
                    'terms_accepted': 'Accept the submission terms to continue.'
                })
        elif self.instance.owner_announcement.status != OwnerAnnouncement.Status.CORRECTIONS_REQUESTED:
            raise serializers.ValidationError({
                'detail': 'Only submissions with requested corrections can be edited.'
            })
        return attrs

    def get_submission_status(self, obj):
        return obj.owner_announcement.status

    def get_review_feedback(self, obj):
        return obj.owner_announcement.broker_feedback

    def get_submission_events(self, obj):
        events = obj.owner_announcement.events.select_related('actor').all()
        return OwnerAnnouncementEventSerializer(events, many=True).data

    def create(self, validated_data):
        user = self.context['request'].user
        owner_contact_name = validated_data.pop('owner_contact_name').strip()
        owner_contact_phone = validated_data.pop('owner_contact_phone').strip()
        owner_contact_email = validated_data.pop('owner_contact_email', '').strip()
        validated_data.pop('authorization_confirmed')
        validated_data.pop('terms_accepted')
        amenities = validated_data.pop('amenities', [])
        if 'area_sqft' in validated_data and 'area_value' not in validated_data:
            area_sqft = validated_data.pop('area_sqft')
            validated_data['area_value'] = area_sqft or None
            validated_data['area_unit'] = Property.AreaUnit.SQUARE_FEET if area_sqft else ''

        property_obj = Property.objects.create(
            owner=user,
            submitted_by=user,
            publication_status=Property.PublicationStatus.PENDING_REVIEW,
            service_type=Property.ServiceType.OWNER_ANNOUNCED,
            status=Property.Status.AVAILABLE,
            advertising_authorized=True,
            contact_publicly_visible=False,
            contact_name='',
            contact_phone='',
            contact_email='',
            **validated_data,
        )
        property_obj.amenities.set(amenities)
        announcement = OwnerAnnouncement.objects.create(
            property=property_obj,
            submitter=user,
            owner_contact_name=owner_contact_name,
            owner_contact_phone=owner_contact_phone,
            owner_contact_email=owner_contact_email,
            authorization_confirmed=True,
            terms_accepted_at=timezone.now(),
        )
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=user,
            event_type=OwnerAnnouncementEvent.Type.SUBMITTED,
            to_status=announcement.status,
        )
        InAppNotification.objects.create(
            recipient=user,
            announcement=announcement,
            notification_type='owner_submission_received',
            message=f'Your property submission "{property_obj.title}" is pending review.',
            idempotency_key=f'owner-submission:{announcement.pk}:received',
        )
        return property_obj

    def update(self, instance, validated_data):
        for field in ('owner_contact_name', 'owner_contact_phone', 'owner_contact_email'):
            setattr(
                instance.owner_announcement,
                field,
                validated_data.pop(field, getattr(instance.owner_announcement, field)),
            )
        validated_data.pop('authorization_confirmed', None)
        validated_data.pop('terms_accepted', None)
        amenities = validated_data.pop('amenities', None)
        if 'area_sqft' in validated_data and 'area_value' not in validated_data:
            area_sqft = validated_data.pop('area_sqft')
            validated_data['area_value'] = area_sqft or None
            validated_data['area_unit'] = Property.AreaUnit.SQUARE_FEET if area_sqft else ''
        announcement = instance.owner_announcement
        before_status = announcement.status
        instance = super().update(instance, validated_data)
        if amenities is not None:
            instance.amenities.set(amenities)
        announcement.status = OwnerAnnouncement.Status.PENDING_REVIEW
        announcement.broker_feedback = ''
        announcement.reviewed_at = None
        announcement.reviewed_by = None
        announcement.save(update_fields=[
            'owner_contact_name',
            'owner_contact_phone',
            'owner_contact_email',
            'status',
            'broker_feedback',
            'reviewed_at',
            'reviewed_by',
            'updated_at',
        ])
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=self.context['request'].user,
            event_type=OwnerAnnouncementEvent.Type.EDITED,
            from_status=before_status,
            to_status=announcement.status,
        )
        return instance


class OwnerAnnouncementReviewSerializer(serializers.ModelSerializer):
    property = OwnerPropertySubmissionSerializer(read_only=True)
    events = OwnerAnnouncementEventSerializer(many=True, read_only=True)

    class Meta:
        model = OwnerAnnouncement
        fields = [
            'id',
            'property',
            'owner_contact_name',
            'owner_contact_phone',
            'owner_contact_email',
            'status',
            'broker_feedback',
            'submitted_at',
            'reviewed_at',
            'reviewed_by_id',
            'events',
        ]
        read_only_fields = fields
