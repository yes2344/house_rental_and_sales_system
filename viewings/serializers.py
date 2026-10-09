from django.utils import timezone
from rest_framework import serializers

from properties.models import Property
from viewings.models import ViewingRequest


class PublicViewingRequestCreateSerializer(serializers.ModelSerializer):
    property_id = serializers.PrimaryKeyRelatedField(
        source='property',
        queryset=Property.objects.filter(
            publication_status=Property.PublicationStatus.PUBLISHED,
            status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE],
        ),
        write_only=True,
    )
    full_name = serializers.CharField(max_length=200, trim_whitespace=True, write_only=True)
    email = serializers.EmailField(write_only=True)
    phone = serializers.CharField(max_length=50, trim_whitespace=True, write_only=True)
    preferred_date = serializers.DateField()
    preferred_time = serializers.TimeField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ViewingRequest
        fields = [
            'id',
            'property_id',
            'full_name',
            'email',
            'phone',
            'preferred_date',
            'preferred_time',
            'message',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def validate_preferred_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError('Preferred date cannot be in the past.')
        return value


class PublicViewingRequestReceiptSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=ViewingRequest.Status.choices)
    created_at = serializers.DateTimeField()


class ManagedViewingPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'title', 'slug', 'location']


class ManagedViewingRequestSerializer(serializers.ModelSerializer):
    property = ManagedViewingPropertySerializer(read_only=True)

    class Meta:
        model = ViewingRequest
        fields = [
            'id',
            'property',
            'full_name',
            'email',
            'phone',
            'preferred_date',
            'preferred_time',
            'message',
            'status',
            'scheduled_date',
            'scheduled_time',
            'agent_notes',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'property',
            'full_name',
            'email',
            'phone',
            'preferred_date',
            'preferred_time',
            'message',
            'created_at',
        ]

    def update(self, instance, validated_data):
        if validated_data.get('status') == ViewingRequest.Status.CONFIRMED:
            if not validated_data.get('scheduled_date') and not instance.scheduled_date:
                validated_data['scheduled_date'] = instance.preferred_date
            if not validated_data.get('scheduled_time') and not instance.scheduled_time:
                validated_data['scheduled_time'] = instance.preferred_time
        return super().update(instance, validated_data)
