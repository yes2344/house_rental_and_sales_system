from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import Profile
from admin.models import AdminAuditEvent, BrokerageSettings, HomepageNote, SocialMediaLink
from properties.models import ListingReport, Property, PropertyBrokerAssignment


User = get_user_model()


class SocialMediaLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaLink
        fields = ['platform', 'url', 'is_enabled', 'display_order']

    def validate_url(self, value):
        if not value.startswith('https://'):
            raise serializers.ValidationError('Enter a secure HTTPS URL.')
        return value


class BrokerageSettingsSerializer(serializers.ModelSerializer):
    social_links = SocialMediaLinkSerializer(many=True, required=False)

    class Meta:
        model = BrokerageSettings
        fields = [
            'business_name',
            'phone',
            'whatsapp_url',
            'telegram_url',
            'email',
            'facebook_url',
            'instagram_url',
            'tiktok_url',
            'youtube_url',
            'linkedin_url',
            'social_links',
        ]

    def validate(self, attrs):
        for field in (
            'whatsapp_url',
            'telegram_url',
            'facebook_url',
            'instagram_url',
            'tiktok_url',
            'youtube_url',
            'linkedin_url',
        ):
            value = attrs.get(field)
            if value and not value.startswith(('https://', 'http://')):
                raise serializers.ValidationError({field: 'Enter an HTTP or HTTPS URL.'})
        return attrs

    def validate_social_links(self, value):
        platforms = [link['platform'] for link in value]
        if len(platforms) != len(set(platforms)):
            raise serializers.ValidationError('Each social platform can only have one link.')
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        social_links = validated_data.pop('social_links', None)
        if social_links is not None:
            links_by_platform = {link['platform']: link['url'] for link in social_links}
            for platform in SocialMediaLink.Platform.values:
                validated_data[f'{platform}_url'] = links_by_platform.get(platform, '')
        instance = super().update(instance, validated_data)
        if social_links is not None:
            instance.social_links.all().delete()
            SocialMediaLink.objects.bulk_create([
                SocialMediaLink(brokerage=instance, **link)
                for link in social_links
            ])
        return instance


class PublicBrokerageSettingsSerializer(BrokerageSettingsSerializer):
    social_links = serializers.SerializerMethodField()

    class Meta(BrokerageSettingsSerializer.Meta):
        fields = ['business_name', 'phone', 'email', 'social_links']

    def get_social_links(self, obj):
        if not obj.pk:
            return []
        queryset = SocialMediaLink.objects.filter(
            brokerage_id=obj.pk,
            is_enabled=True,
        ).order_by('display_order', 'platform')
        return SocialMediaLinkSerializer(queryset, many=True).data


class HomepageNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomepageNote
        fields = ['id', 'title', 'text', 'is_published', 'display_order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Enter note text.')
        return value


class AdminRoleField(serializers.ChoiceField):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        if instance.is_superuser:
            return 'owner'
        if instance.is_staff:
            return 'administrator'
        profile = getattr(instance, 'profile', None)
        return profile.role if profile else None


class AdminBrokerApprovalField(serializers.BooleanField):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        profile = getattr(instance, 'profile', None)
        return bool(profile and profile.broker_approved)


class AdminUserSerializer(serializers.ModelSerializer):
    role = AdminRoleField(choices=Profile.Role.choices, read_only=True)
    broker_approved = AdminBrokerApprovalField(read_only=True)
    management_permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=Profile.Permission.choices),
        source='profile.management_permissions',
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'role',
            'broker_approved',
            'management_permissions',
            'date_joined',
        ]
        read_only_fields = ['id', 'username', 'is_staff', 'is_superuser', 'date_joined']

    def to_internal_value(self, data):
        privileged_fields = {'is_staff', 'is_superuser', 'role', 'broker_approved', 'management_permissions'} & data.keys()
        if privileged_fields:
            raise serializers.ValidationError(
                {field: 'Roles and permissions are managed through the owner-only delegated-account interface.' for field in privileged_fields}
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        if self.instance and (self.instance.is_staff or self.instance.is_superuser):
            raise serializers.ValidationError('Privileged accounts are managed through the owner-only interface.')
        if self.instance and self.instance.pk == self.context['request'].user.pk:
            if attrs.get('is_active') is False:
                raise serializers.ValidationError({'is_active': 'You cannot deactivate your own account.'})
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class AdminPropertySerializer(serializers.ModelSerializer):
    moderation_note = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True,
        write_only=True,
    )
    owner_id = serializers.IntegerField(read_only=True, allow_null=True)
    submitted_by_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Property
        fields = [
            'id',
            'title',
            'slug',
            'location',
            'property_type',
            'listing_type',
            'price',
            'status',
            'publication_status',
            'is_featured',
            'owner_id',
            'submitted_by_id',
            'moderation_note',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'title',
            'slug',
            'location',
            'property_type',
            'listing_type',
            'price',
            'owner_id',
            'submitted_by_id',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs):
        publication_status = attrs.get(
            'publication_status',
            self.instance.publication_status if self.instance else Property.PublicationStatus.PENDING_REVIEW,
        )
        property_status = attrs.get(
            'status',
            self.instance.status if self.instance else Property.Status.AVAILABLE,
        )
        listing_type = self.instance.listing_type if self.instance else Property.ListingType.SALE
        moderation_statuses = (
            Property.PublicationStatus.REJECTED,
            Property.PublicationStatus.SUSPENDED,
        )
        if attrs.get('publication_status') in moderation_statuses and not attrs.get(
            'moderation_note',
            '',
        ).strip():
            raise serializers.ValidationError(
                {'moderation_note': 'A reason is required when rejecting or suspending a listing.'}
            )
        if publication_status == Property.PublicationStatus.PUBLISHED and property_status not in (
            Property.Status.AVAILABLE,
            Property.Status.LEGACY_ACTIVE,
        ):
            raise serializers.ValidationError(
                {'publication_status': 'Only available properties can be published.'}
            )
        if property_status == Property.Status.RENTED and listing_type != Property.ListingType.RENT:
            raise serializers.ValidationError({'status': 'Only rental listings can be marked rented.'})
        if property_status == Property.Status.SOLD and listing_type != Property.ListingType.SALE:
            raise serializers.ValidationError({'status': 'Only sale listings can be marked sold.'})
        return attrs


class PublicListingReportSerializer(serializers.ModelSerializer):
    property_id = serializers.PrimaryKeyRelatedField(
        source='property',
        queryset=Property.objects.filter(
            publication_status=Property.PublicationStatus.PUBLISHED,
            status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE],
        ),
        write_only=True,
    )

    class Meta:
        model = ListingReport
        fields = ['id', 'property_id', 'reporter_name', 'reporter_email', 'reason', 'details', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_reporter_name(self, value):
        return value.strip()


class PublicReportReceiptSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=ListingReport.Status.choices)
    created_at = serializers.DateTimeField()


class AdminListingReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingReport
        fields = [
            'id',
            'property',
            'property_title',
            'reporter_name',
            'reporter_email',
            'reason',
            'details',
            'status',
            'moderator_notes',
            'reviewed_by',
            'reviewed_at',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'property',
            'property_title',
            'reporter_name',
            'reporter_email',
            'reason',
            'details',
            'reviewed_by',
            'reviewed_at',
            'created_at',
        ]

    def update(self, instance, validated_data):
        result = super().update(instance, validated_data)
        if result.status == ListingReport.Status.PENDING:
            result.reviewed_by = None
            result.reviewed_at = None
        else:
            result.reviewed_by = self.context['request'].user
            result.reviewed_at = timezone.now()
        result.save(update_fields=['reviewed_by', 'reviewed_at'])
        return result


class AdminAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminAuditEvent
        fields = [
            'id',
            'actor_username',
            'action',
            'object_type',
            'object_id',
            'changes',
            'created_at',
        ]


class AdminBrokerAssignmentSerializer(serializers.ModelSerializer):
    broker_id = serializers.PrimaryKeyRelatedField(
        source='broker',
        queryset=User.objects.filter(
            profile__role=Profile.Role.BROKER,
            profile__broker_approved=True,
        ),
        required=True,
    )
    broker_username = serializers.CharField(source='broker.username', read_only=True)
    granted_by_username = serializers.CharField(source='granted_by.username', read_only=True, allow_null=True)

    class Meta:
        model = PropertyBrokerAssignment
        fields = ['id', 'broker_id', 'broker_username', 'granted_by_username', 'granted_at']
        read_only_fields = ['id', 'broker_username', 'granted_by_username', 'granted_at']
