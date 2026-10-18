from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from properties.models import Property
from properties.access import public_properties
from viewings.models import ViewingRequest, ViewingRequestEvent


def appointment_is_in_past(appointment_date, appointment_time):
    if appointment_date is None:
        return True
    local_now = timezone.localtime()
    return appointment_date < local_now.date() or (
        appointment_date == local_now.date()
        and appointment_time is not None
        and appointment_time <= local_now.time().replace(tzinfo=None)
    )


class PublicViewingRequestCreateSerializer(serializers.ModelSerializer):
    property_id = serializers.PrimaryKeyRelatedField(
        source='property',
        queryset=public_properties(),
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

    def validate(self, attrs):
        preferred_date = attrs.get('preferred_date')
        preferred_time = attrs.get('preferred_time')
        if preferred_date and preferred_time and appointment_is_in_past(preferred_date, preferred_time):
            raise serializers.ValidationError({
                'preferred_time': 'Preferred time cannot be in the past.'
            })
        return attrs


class PublicViewingRequestReceiptSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=ViewingRequest.Status.choices)
    created_at = serializers.DateTimeField()


class GuestViewingRequestStatusSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source='property.title', read_only=True)
    appointment_timezone = serializers.SerializerMethodField()

    class Meta:
        model = ViewingRequest
        fields = [
            'id',
            'property_title',
            'status',
            'preferred_date',
            'preferred_time',
            'proposed_date',
            'proposed_time',
            'scheduled_date',
            'scheduled_time',
            'appointment_timezone',
            'created_at',
        ]
        read_only_fields = fields

    def get_appointment_timezone(self, obj) -> str:
        return settings.TIME_ZONE


class GuestViewingRequestDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['accept', 'decline'])


class ViewingRequestEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ViewingRequestEvent
        fields = [
            'event_type',
            'from_status',
            'to_status',
            'proposed_date',
            'proposed_time',
            'actor_name',
            'message',
            'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj) -> str | None:
        return obj.actor.get_username() if obj.actor_id else None


class ManagedViewingPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'title', 'slug', 'location']


class ManagedViewingRequestSerializer(serializers.ModelSerializer):
    property = ManagedViewingPropertySerializer(read_only=True)
    events = ViewingRequestEventSerializer(many=True, read_only=True)
    appointment_timezone = serializers.SerializerMethodField()

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
            'proposed_date',
            'proposed_time',
            'status',
            'scheduled_date',
            'scheduled_time',
            'agent_notes',
            'appointment_timezone',
            'events',
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
            'scheduled_date',
            'scheduled_time',
            'appointment_timezone',
            'events',
            'created_at',
        ]

    def get_appointment_timezone(self, obj) -> str:
        return settings.TIME_ZONE

    def validate_proposed_date(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError('Proposed date cannot be in the past.')
        return value

    def validate(self, attrs):
        requested_status = attrs.get('status')
        if requested_status == ViewingRequest.Status.CONFIRMED:
            raise serializers.ValidationError({
                'status': 'Only the visitor can confirm a proposed appointment.'
            })

        proposed_date = attrs.get('proposed_date', self.instance.proposed_date)
        proposed_time = attrs.get('proposed_time', self.instance.proposed_time)
        proposal_changed = (
            ('proposed_date' in attrs and attrs['proposed_date'] != self.instance.proposed_date)
            or ('proposed_time' in attrs and attrs['proposed_time'] != self.instance.proposed_time)
        )
        if proposal_changed and (proposed_date is None or proposed_time is None):
            raise serializers.ValidationError({
                'proposed_date': 'An appointment proposal requires both a date and a time.'
            })
        if proposal_changed and self.instance.status not in (
            ViewingRequest.Status.PENDING,
            ViewingRequest.Status.PROPOSED,
            ViewingRequest.Status.DECLINED,
        ):
            raise serializers.ValidationError({
                'proposed_date': 'A closed or confirmed request cannot receive a new proposal.'
            })
        if proposal_changed and appointment_is_in_past(proposed_date, proposed_time):
            raise serializers.ValidationError({
                'proposed_time': 'Proposed appointment time cannot be in the past.'
            })
        if proposal_changed and requested_status == ViewingRequest.Status.REJECTED:
            raise serializers.ValidationError({
                'status': 'A proposal cannot be sent and rejected in the same update.'
            })
        if requested_status == ViewingRequest.Status.REJECTED and self.instance.status not in (
            ViewingRequest.Status.PENDING,
            ViewingRequest.Status.PROPOSED,
        ):
            raise serializers.ValidationError({
                'status': 'Only a pending request or open proposal can be rejected.'
            })
        if requested_status not in (None, ViewingRequest.Status.REJECTED):
            raise serializers.ValidationError({
                'status': 'Managers may propose an appointment or reject a request.'
            })
        return attrs

    def update(self, instance, validated_data):
        requested_status = validated_data.pop('status', None)
        previous_status = instance.status
        proposal_changed = (
            ('proposed_date' in validated_data and validated_data['proposed_date'] != instance.proposed_date)
            or ('proposed_time' in validated_data and validated_data['proposed_time'] != instance.proposed_time)
        )
        if proposal_changed:
            validated_data['status'] = ViewingRequest.Status.PROPOSED
        elif requested_status == ViewingRequest.Status.REJECTED:
            validated_data['status'] = ViewingRequest.Status.REJECTED

        updated = super().update(instance, validated_data)
        if proposal_changed:
            event_type = (
                ViewingRequestEvent.Type.PROPOSAL_REVISED
                if previous_status == ViewingRequest.Status.PROPOSED
                else ViewingRequestEvent.Type.PROPOSAL_SENT
            )
            ViewingRequestEvent.objects.create(
                viewing_request=updated,
                actor=self.context['request'].user,
                event_type=event_type,
                from_status=previous_status,
                to_status=updated.status,
                proposed_date=updated.proposed_date,
                proposed_time=updated.proposed_time,
            )
        elif requested_status == ViewingRequest.Status.REJECTED and previous_status != updated.status:
            ViewingRequestEvent.objects.create(
                viewing_request=updated,
                actor=self.context['request'].user,
                event_type=ViewingRequestEvent.Type.REJECTED,
                from_status=previous_status,
                to_status=updated.status,
            )
        if hasattr(updated, '_prefetched_objects_cache'):
            updated._prefetched_objects_cache.pop('events', None)
        return updated


class CustomerViewingPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'title', 'slug', 'listing_type', 'status', 'location']


class CustomerViewingRequestSerializer(serializers.ModelSerializer):
    property = CustomerViewingPropertySerializer(read_only=True)
    events = ViewingRequestEventSerializer(many=True, read_only=True)
    appointment_timezone = serializers.SerializerMethodField()

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
            'proposed_date',
            'proposed_time',
            'scheduled_date',
            'scheduled_time',
            'status',
            'appointment_timezone',
            'events',
            'created_at',
        ]
        read_only_fields = fields

    def get_appointment_timezone(self, obj) -> str:
        return settings.TIME_ZONE


class ViewingRequestResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['accept', 'decline'])
    message = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ViewingRequestCancellationSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ManagedViewingRequestActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['confirm_requested', 'cancel', 'complete'])
    message = serializers.CharField(required=False, allow_blank=True, max_length=2000)
