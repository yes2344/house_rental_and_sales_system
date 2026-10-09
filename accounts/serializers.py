from collections.abc import Mapping

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from accounts.models import DelegatedAccountInvitation, Profile, UserPreferences
from favorites.models import Favorite
from properties.models import Property
from viewings.models import ViewingRequest


User = get_user_model()


class ProfilePhoneField(serializers.CharField):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        profile = Profile.objects.filter(user_id=instance.pk).only('phone').first()
        return profile.phone if profile else ''


class AccountSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    phone = ProfilePhoneField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone']
        read_only_fields = ['id', 'username', 'role']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_role(self, obj):
        if obj.is_superuser:
            return 'owner'
        if obj.is_staff:
            return 'administrator'
        profile = getattr(obj, 'profile', None)
        return profile.role if profile else None

    @transaction.atomic
    def update(self, instance, validated_data):
        phone = validated_data.pop('phone', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if phone is not None:
            profile, _ = Profile.objects.get_or_create(
                user=instance,
                defaults={'role': Profile.Role.CUSTOMER},
            )
            profile.phone = phone
            profile.save(update_fields=['phone', 'updated_at'])
        return instance


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_password(self, value):
        candidate_user = User(
            username=self.initial_data.get('username', ''),
            email=self.initial_data.get('email', ''),
        )
        try:
            password_validation.validate_password(value, user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    @transaction.atomic
    def create(self, validated_data):
        phone = validated_data.pop('phone', '')
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, role=Profile.Role.CUSTOMER, phone=phone)
        return user


class DelegatedAccountSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=[(Profile.Role.ADMINISTRATOR, 'Administrator'), (Profile.Role.BROKER, 'Broker')],
        source='profile.role',
    )
    management_permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=Profile.Permission.choices),
        source='profile.management_permissions',
        allow_empty=True,
        required=False,
    )
    broker_approved = serializers.BooleanField(source='profile.broker_approved', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'role',
            'is_active',
            'broker_approved',
            'management_permissions',
            'date_joined',
        ]
        read_only_fields = ['id', 'username', 'broker_approved', 'date_joined']

    def validate_management_permissions(self, permissions):
        owner_only = {
            Profile.Permission.SETTINGS_MANAGE,
            Profile.Permission.STAFF_MANAGE,
        }
        if owner_only.intersection(permissions):
            raise serializers.ValidationError('These permissions are reserved for the platform owner.')
        role = self.initial_data.get(
            'role',
            self.instance.profile.role if self.instance else None,
        )
        if role == Profile.Role.BROKER:
            broker_permissions = {
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            }
            unsupported = set(permissions) - broker_permissions
            if unsupported:
                raise serializers.ValidationError(
                    'Brokers can only receive assigned-listing and assigned-viewing permissions.'
                )
        return list(dict.fromkeys(permissions))

    def validate_email(self, value):
        existing = User.objects.filter(email__iexact=value)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, attrs):
        profile_data = attrs.get('profile', {})
        role = profile_data.get(
            'role',
            self.instance.profile.role if self.instance else None,
        )
        permissions = profile_data.get(
            'management_permissions',
            self.instance.profile.management_permissions if self.instance else [],
        )
        owner_only = {
            Profile.Permission.SETTINGS_MANAGE,
            Profile.Permission.STAFF_MANAGE,
        }
        if owner_only.intersection(permissions):
            raise serializers.ValidationError(
                {'management_permissions': 'These permissions are reserved for the platform owner.'}
            )
        if role == Profile.Role.BROKER:
            allowed = {
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            }
            if set(permissions) - allowed:
                raise serializers.ValidationError(
                    {'management_permissions': 'Brokers may receive only assigned-work permissions.'}
                )
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        permissions = profile_data.get('management_permissions')
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        profile = instance.profile
        role = profile_data.get('role', profile.role)
        if role not in (Profile.Role.ADMINISTRATOR, Profile.Role.BROKER):
            raise serializers.ValidationError({'role': 'Delegated accounts must remain administrator or broker.'})
        profile.role = role
        profile.broker_approved = role == Profile.Role.BROKER
        if permissions is not None:
            profile.management_permissions = permissions
        profile.save(update_fields=['role', 'broker_approved', 'management_permissions', 'updated_at'])
        instance.is_staff = role == Profile.Role.ADMINISTRATOR
        instance.save(update_fields=['is_staff'])
        return instance


class DelegatedAccountCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[(Profile.Role.ADMINISTRATOR, 'Administrator'), (Profile.Role.BROKER, 'Broker')],
    )
    management_permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=Profile.Permission.choices),
        allow_empty=True,
        required=False,
        default=list,
    )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_management_permissions(self, permissions):
        return DelegatedAccountSerializer(
            data={
                'role': self.initial_data.get('role'),
                'management_permissions': permissions,
                'username': 'validation-only',
                'email': 'validation@example.invalid',
            }
        ).validate_management_permissions(permissions)

    @transaction.atomic
    def create(self, validated_data):
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        user = user_model(
            username=validated_data['username'],
            email=validated_data['email'],
            is_active=False,
            is_staff=validated_data['role'] == Profile.Role.ADMINISTRATOR,
        )
        user.set_unusable_password()
        user.save()
        Profile.objects.create(
            user=user,
            role=validated_data['role'],
            broker_approved=validated_data['role'] == Profile.Role.BROKER,
            management_permissions=validated_data['management_permissions'],
        )
        invitation, token = DelegatedAccountInvitation.issue(user, self.context['request'].user)
        self.invitation = invitation
        self.invitation_token = token
        return user


class DelegatedInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        digest = DelegatedAccountInvitation.digest(attrs['token'])
        invitation = (
            DelegatedAccountInvitation.objects.select_related('user')
            .filter(token_digest=digest)
            .first()
        )
        if invitation is None or not invitation.is_valid():
            raise serializers.ValidationError({'token': 'This invitation is invalid, expired, or already used.'})
        try:
            password_validation.validate_password(attrs['password'], user=invitation.user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages}) from exc
        attrs['invitation_id'] = invitation.pk
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        invitation = (
            DelegatedAccountInvitation.objects.select_for_update()
            .select_related('user')
            .get(pk=self.validated_data['invitation_id'])
        )
        if not invitation.is_valid():
            raise serializers.ValidationError({'token': 'This invitation is invalid, expired, or already used.'})
        user = invitation.user
        user.set_password(self.validated_data['password'])
        user.is_active = True
        user.save(update_fields=['password', 'is_active'])
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['accepted_at'])
        from admin.audit import record_admin_action

        record_admin_action(
            user,
            action='delegated_invitation_accepted',
            object_type='user',
            object_id=user.pk,
            changes={'role': user.profile.role},
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        user = authenticate(
            request=self.context.get('request'),
            username=attrs['username'],
            password=attrs['password'],
        )
        if user is None:
            raise serializers.ValidationError('Invalid username or password.')
        attrs['user'] = user
        return attrs


class CsrfTokenSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()


class LoginResponseSerializer(AccountSerializer):
    csrf_token = serializers.CharField()

    class Meta(AccountSerializer.Meta):
        fields = AccountSerializer.Meta.fields + ['csrf_token']


class EmptySerializer(serializers.Serializer):
    pass


class ActivityPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'title', 'slug', 'listing_type', 'status']


class FavoriteActivitySerializer(serializers.ModelSerializer):
    property = ActivityPropertySerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'property', 'created_at']


class ViewingRequestActivitySerializer(serializers.ModelSerializer):
    property = ActivityPropertySerializer(read_only=True)

    class Meta:
        model = ViewingRequest
        fields = [
            'id',
            'property',
            'status',
            'preferred_date',
            'preferred_time',
            'scheduled_date',
            'scheduled_time',
            'created_at',
        ]


class AccountActivitySerializer(serializers.Serializer):
    favorites = FavoriteActivitySerializer(many=True)
    viewing_requests = ViewingRequestActivitySerializer(many=True)


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = ['theme', 'locale', 'density', 'reduced_motion']

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError({
                    field: ['Unknown or unsupported preference.']
                    for field in sorted(unknown_fields)
                })
        return super().to_internal_value(data)
