from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from accounts.models import Profile
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
