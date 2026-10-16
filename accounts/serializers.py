from collections.abc import Mapping

from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from accounts.email_messages import get_user_from_uid
from accounts.models import (
    DelegatedAccountInvitation,
    EmailVerificationToken,
    Profile,
    TabSessionToken,
    UserPreferences,
)
from accounts.permissions import broker_work_permissions, effective_management_permissions, is_platform_owner
from favorites.models import Favorite
from properties.models import Location, Property
from viewings.models import ViewingRequest


User = get_user_model()


class ProfilePhoneField(serializers.CharField):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        profile = Profile.objects.filter(user_id=instance.pk).only('phone').first()
        return profile.phone if profile else ''


class EffectiveManagementPermissionsField(serializers.ListField):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        return effective_management_permissions(instance)


class AccountSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    phone = ProfilePhoneField(required=False, allow_blank=True)
    management_permissions = serializers.SerializerMethodField()
    is_platform_owner = serializers.SerializerMethodField()
    broker_onboarding_required = serializers.SerializerMethodField()
    broker_password_changed = serializers.SerializerMethodField()
    assigned_city_id = serializers.SerializerMethodField()
    assigned_city_name = serializers.SerializerMethodField()
    assigned_city_name_am = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone',
            'management_permissions',
            'is_platform_owner',
            'broker_onboarding_required',
            'broker_password_changed',
            'assigned_city_id',
            'assigned_city_name',
            'assigned_city_name_am',
        ]
        read_only_fields = [
            'id',
            'username',
            'role',
            'management_permissions',
            'is_platform_owner',
            'broker_onboarding_required',
            'broker_password_changed',
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_role(self, obj):
        if obj.is_superuser:
            return Profile.Role.ADMINISTRATOR
        if obj.is_staff:
            return 'administrator'
        profile = getattr(obj, 'profile', None)
        return profile.role if profile else None

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_management_permissions(self, obj):
        return effective_management_permissions(obj)

    @extend_schema_field(serializers.BooleanField())
    def get_is_platform_owner(self, obj):
        return is_platform_owner(obj)

    @extend_schema_field(serializers.BooleanField())
    def get_broker_onboarding_required(self, obj):
        profile = getattr(obj, 'profile', None)
        return bool(profile and profile.broker_onboarding_required)

    @extend_schema_field(serializers.BooleanField())
    def get_broker_password_changed(self, obj):
        profile = getattr(obj, 'profile', None)
        return bool(profile and profile.broker_password_changed)

    def get_assigned_city_id(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.assigned_city_id if profile else None

    def get_assigned_city_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.assigned_city.name if profile and profile.assigned_city_id else None

    def get_assigned_city_name_am(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.assigned_city.name_am if profile and profile.assigned_city_id else None

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
    next_path = serializers.CharField(max_length=2048, required=False, default='/')

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

    def validate_next_path(self, value):
        if (
            not value.startswith('/')
            or value.startswith('//')
            or '\\' in value
            or any(ord(char) < 32 for char in value)
        ):
            raise serializers.ValidationError('The return path must be a local application path.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        from accounts.email_messages import send_verification_email

        phone = validated_data.pop('phone', '')
        next_path = validated_data.pop('next_path', '/')
        user = User.objects.create_user(is_active=False, **validated_data)
        Profile.objects.create(user=user, role=Profile.Role.CUSTOMER, phone=phone)
        _, token = EmailVerificationToken.issue(user)
        send_verification_email(user, token, next_path)
        return user


class EmailAddressSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailVerificationSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        user = get_user_from_uid(attrs['uid'])
        if (
            not user
            or user.is_active
            or user.is_staff
            or user.is_superuser
            or not Profile.objects.filter(user=user, role=Profile.Role.CUSTOMER).exists()
        ):
            raise serializers.ValidationError('This verification link is invalid or expired.')
        verification = EmailVerificationToken.objects.filter(
            user=user,
            token_digest=EmailVerificationToken.digest(attrs['token']),
            email__iexact=user.email,
            expires_at__gt=timezone.now(),
        ).first()
        if not verification:
            raise serializers.ValidationError('This verification link is invalid or expired.')
        attrs['user'] = user
        attrs['verification'] = verification
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = User.objects.select_for_update().get(pk=self.validated_data['user'].pk)
        token = EmailVerificationToken.objects.select_for_update().filter(
            pk=self.validated_data['verification'].pk,
            user=user,
            token_digest=EmailVerificationToken.digest(self.validated_data['token']),
            email__iexact=user.email,
            expires_at__gt=timezone.now(),
        ).first()
        if user.is_active or not token:
            raise serializers.ValidationError('This verification link is invalid or expired.')
        user.is_active = True
        user.save(update_fields=['is_active'])
        EmailVerificationToken.objects.filter(user=user).delete()
        return user


class PasswordResetSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = get_user_from_uid(attrs['uid'])
        if (
            not user
            or not user.is_active
            or not default_token_generator.check_token(user, attrs['token'])
        ):
            raise serializers.ValidationError('This password reset link is invalid or expired.')
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError({'password_confirmation': 'Passwords do not match.'})
        try:
            password_validation.validate_password(attrs['password'], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages}) from exc
        attrs['user'] = user
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = User.objects.select_for_update().get(pk=self.validated_data['user'].pk)
        if (
            not user.is_active
            or not default_token_generator.check_token(user, self.validated_data['token'])
        ):
            raise serializers.ValidationError('This password reset link is invalid or expired.')
        user.set_password(self.validated_data['password'])
        user.save(update_fields=['password'])
        TabSessionToken.objects.filter(
            user=user,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        return user


class DelegatedAccountSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(source='profile.phone', max_length=50, required=False, allow_blank=True)
    initial_password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    role = serializers.ChoiceField(
        choices=[(Profile.Role.BROKER, 'Agent')],
        source='profile.role',
    )
    assigned_city_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(
            location_type=Location.Type.CITY,
            is_active=True,
        ),
        source='profile.assigned_city',
        required=False,
    )
    management_permissions = EffectiveManagementPermissionsField(
        child=serializers.ChoiceField(choices=Profile.Permission.choices),
        source='profile.management_permissions',
        allow_empty=True,
        required=False,
    )
    broker_approved = serializers.BooleanField(source='profile.broker_approved', read_only=True)
    broker_onboarding_required = serializers.BooleanField(
        source='profile.broker_onboarding_required',
        read_only=True,
    )
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'initial_password',
            'email',
            'first_name',
            'last_name',
            'phone',
            'role',
            'assigned_city_id',
            'is_active',
            'broker_approved',
            'broker_onboarding_required',
            'management_permissions',
            'date_joined',
        ]
        read_only_fields = ['id', 'broker_approved', 'broker_onboarding_required', 'date_joined']

    def validate_username(self, value):
        existing = User.objects.filter(username__iexact=value)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_initial_password(self, value):
        candidate_user = User(
            username=self.initial_data.get('username') or getattr(self.instance, 'username', ''),
            email=self.initial_data.get('email') or getattr(self.instance, 'email', ''),
            first_name=self.initial_data.get('first_name') or getattr(self.instance, 'first_name', ''),
            last_name=self.initial_data.get('last_name') or getattr(self.instance, 'last_name', ''),
        )
        try:
            password_validation.validate_password(value, user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate_management_permissions(self, permissions):
        owner_only = {Profile.Permission.STAFF_MANAGE, Profile.Permission.SETTINGS_MANAGE}
        owner_is_actor = is_platform_owner(self.context['request'].user)
        if owner_only.intersection(permissions) and not owner_is_actor:
            raise serializers.ValidationError('These permissions are reserved for the platform owner.')
        permitted = set(broker_work_permissions())
        if owner_is_actor:
            permitted.add(Profile.Permission.SETTINGS_MANAGE)
        unsupported = set(permissions) - permitted
        if unsupported:
            raise serializers.ValidationError(
                'Agents can only receive agent-work permissions.'
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
        if role != Profile.Role.BROKER:
            raise serializers.ValidationError(
                {'role': 'This endpoint manages agent accounts only.'}
            )
        permissions = profile_data.get(
            'management_permissions',
            self.instance.profile.management_permissions if self.instance else [],
        )
        if not self.instance:
            if profile_data.get('assigned_city') is None:
                raise serializers.ValidationError({
                    'assigned_city': 'Assign an active city to this agent account.',
                })
            profile_data['management_permissions'] = broker_work_permissions()
            permissions = profile_data['management_permissions']
        owner_only = {Profile.Permission.STAFF_MANAGE, Profile.Permission.SETTINGS_MANAGE}
        owner_is_actor = is_platform_owner(self.context['request'].user)
        if owner_only.intersection(permissions) and not owner_is_actor:
            raise serializers.ValidationError(
                {'management_permissions': 'These permissions are reserved for the platform owner.'}
            )
        permitted = set(broker_work_permissions())
        if owner_is_actor:
            permitted.add(Profile.Permission.SETTINGS_MANAGE)
        if set(permissions) - permitted:
            raise serializers.ValidationError(
                {'management_permissions': 'Agents may receive only agent-work permissions.'}
            )
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        permissions = profile_data.get('management_permissions')
        initial_password = validated_data.pop('initial_password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if initial_password:
            instance.set_password(initial_password)
        instance.save()

        profile = instance.profile
        role = profile_data.get('role', profile.role)
        if role != Profile.Role.BROKER:
            raise serializers.ValidationError({'role': 'This endpoint manages agent accounts only.'})
        profile.role = role
        profile.assigned_city = profile_data.get('assigned_city', profile.assigned_city)
        if permissions is not None:
            profile.management_permissions = permissions
        profile.phone = profile_data.get('phone', profile.phone)
        if initial_password:
            profile.broker_approved = False
            profile.broker_onboarding_required = True
            profile.broker_password_changed = False
        profile.save(update_fields=[
            'role',
            'assigned_city',
            'management_permissions',
            'phone',
            'broker_approved',
            'broker_onboarding_required',
            'broker_password_changed',
            'updated_at',
        ])
        instance.is_staff = False
        instance.save(update_fields=['is_staff'])
        return instance


class DelegatedAccountCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    assigned_city_id = serializers.PrimaryKeyRelatedField(
        source='assigned_city',
        queryset=Location.objects.filter(
            location_type=Location.Type.CITY,
            is_active=True,
        ),
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError({
                    field: ['Unknown or unsupported field.']
                    for field in sorted(unknown_fields)
                })
        return super().to_internal_value(data)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_password(self, value):
        candidate_user = User(username=self.initial_data.get('username', ''))
        try:
            password_validation.validate_password(value, user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    @transaction.atomic
    def create(self, validated_data):
        assigned_city = validated_data.pop('assigned_city')
        user = User(
            username=validated_data['username'],
            is_active=True,
            is_staff=False,
        )
        user.set_password(validated_data['password'])
        user.save()
        Profile.objects.create(
            user=user,
            role=Profile.Role.BROKER,
            assigned_city=assigned_city,
            broker_approved=False,
            broker_onboarding_required=True,
            broker_password_changed=False,
            management_permissions=broker_work_permissions(),
        )
        return user


class BrokerFirstLoginPasswordSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        if not value:
            return value
        request = self.context['request']
        existing = User.objects.filter(username__iexact=value).exclude(pk=request.user.pk)
        if existing.exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_new_password(self, value):
        request = self.context['request']
        candidate_user = User(
            username=self.initial_data.get('username') or request.user.username,
            email=request.user.email,
            first_name=request.user.first_name,
            last_name=request.user.last_name,
        )
        try:
            password_validation.validate_password(value, user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate(self, attrs):
        profile = getattr(self.context['request'].user, 'profile', None)
        if (
            profile is None
            or profile.role != Profile.Role.BROKER
            or not profile.broker_onboarding_required
            or profile.broker_password_changed
        ):
            raise serializers.ValidationError('This account is not waiting for its initial password change.')
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        request = self.context['request']
        user = User.objects.select_for_update().get(pk=request.user.pk)
        profile = Profile.objects.select_for_update().get(user=user)
        if (
            profile.role != Profile.Role.BROKER
            or not profile.broker_onboarding_required
            or profile.broker_password_changed
        ):
            raise serializers.ValidationError('This account is not waiting for its initial password change.')
        username = self.validated_data.get('username')
        if username:
            user.username = username
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['username', 'password'])
        profile.broker_password_changed = True
        profile.save(update_fields=['broker_password_changed', 'updated_at'])
        from accounts.models import TabSessionToken

        TabSessionToken.objects.filter(user=user, revoked_at__isnull=True).exclude(
            pk=getattr(request.auth, 'pk', None),
        ).update(revoked_at=timezone.now())
        from admin.audit import record_admin_action

        record_admin_action(
            user,
            action='broker_initial_password_changed',
            object_type='user',
            object_id=user.pk,
            changes={'username_changed': bool(username)},
        )
        return user


class BrokerFirstLoginProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=50)

    def validate_email(self, value):
        existing = User.objects.filter(email__iexact=value).exclude(
            pk=self.context['request'].user.pk,
        )
        if existing.exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, attrs):
        profile = getattr(self.context['request'].user, 'profile', None)
        if (
            profile is None
            or profile.role != Profile.Role.BROKER
            or not profile.broker_onboarding_required
            or not profile.broker_password_changed
        ):
            raise serializers.ValidationError('Change the initial password before completing your agent profile.')
        if profile.assigned_city_id is None:
            raise serializers.ValidationError(
                'Contact an administrator to assign your city before completing agent setup.'
            )
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        request = self.context['request']
        user = User.objects.select_for_update().get(pk=request.user.pk)
        profile = Profile.objects.select_for_update().get(user=user)
        if (
            profile.role != Profile.Role.BROKER
            or not profile.broker_onboarding_required
            or not profile.broker_password_changed
        ):
            raise serializers.ValidationError('Change the initial password before completing your agent profile.')
        for field in ('first_name', 'last_name', 'email'):
            setattr(user, field, self.validated_data[field])
        user.save(update_fields=['first_name', 'last_name', 'email'])
        profile.phone = self.validated_data['phone']
        profile.broker_onboarding_required = False
        profile.broker_approved = True
        profile.management_permissions = broker_work_permissions()
        profile.save(update_fields=[
            'phone',
            'broker_onboarding_required',
            'broker_approved',
            'management_permissions',
            'updated_at',
        ])
        from admin.audit import record_admin_action

        record_admin_action(
            user,
            action='broker_onboarding_completed',
            object_type='user',
            object_id=user.pk,
            changes={'role': profile.role},
        )
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
        profile = user.profile
        if profile.role == Profile.Role.BROKER:
            profile.broker_approved = False
            profile.broker_onboarding_required = True
            profile.broker_password_changed = True
            profile.save(update_fields=[
                'broker_approved',
                'broker_onboarding_required',
                'broker_password_changed',
                'updated_at',
            ])
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['accepted_at'])
        from admin.audit import record_admin_action

        record_admin_action(
            user,
            action='delegated_invitation_accepted',
            object_type='user',
            object_id=user.pk,
            changes={'role': profile.role},
        )
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=False)
    username = serializers.CharField(required=False, write_only=True)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        identifier = (attrs.get('identifier') or attrs.get('username') or '').strip()
        missing = {}
        if not identifier:
            missing['username'] = 'Enter your email address, phone, or username.'
        if not attrs.get('password'):
            missing['password'] = 'This field is required.'
        if missing:
            raise serializers.ValidationError(missing)
        if '@' in identifier:
            matches = list(User.objects.filter(email__iexact=identifier)[:2])
        else:
            phone_matches = list(
                User.objects.filter(profile__phone__iexact=identifier).distinct()[:2]
            )
            matches = phone_matches or list(User.objects.filter(username__iexact=identifier)[:2])
        if len(matches) != 1:
            raise serializers.ValidationError('Invalid username or password.')

        user = authenticate(
            request=self.context.get('request'),
            username=matches[0].username,
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
    session_token = serializers.CharField()

    class Meta(AccountSerializer.Meta):
        fields = AccountSerializer.Meta.fields + ['csrf_token', 'session_token']


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
