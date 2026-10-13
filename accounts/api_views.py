from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import Profile, TabSessionToken, UserPreferences
from accounts.serializers import (
    AccountActivitySerializer,
    AccountSerializer,
    CsrfTokenSerializer,
    DelegatedInvitationAcceptSerializer,
    EmptySerializer,
    LoginResponseSerializer,
    LoginSerializer,
    RegistrationSerializer,
    UserPreferencesSerializer,
)
from favorites.models import Favorite
from viewings.models import ViewingRequest


class CsrfTokenView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = CsrfTokenSerializer

    @extend_schema(summary='Get a CSRF token for browser login requests')
    def get(self, request):
        return Response({'csrf_token': get_token(request)})


class RegistrationView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'account_registration'
    serializer_class = RegistrationSerializer

    @extend_schema(
        summary='Register a customer account',
        responses={201: AccountSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AccountSerializer(user).data, status=status.HTTP_201_CREATED)


class DelegatedInvitationAcceptView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'delegated_invitation_accept'
    serializer_class = DelegatedInvitationAcceptSerializer

    @extend_schema(
        summary='Accept an owner-issued administrator or broker invitation',
        request=DelegatedInvitationAcceptSerializer,
        responses={200: AccountSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AccountSerializer(user).data, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name='dispatch')
class LoginView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'account_login'
    serializer_class = LoginSerializer

    @extend_schema(
        request=LoginSerializer,
        responses={200: LoginResponseSerializer},
        summary='Start an independent tab-scoped API session',
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        _, session_token = TabSessionToken.issue(user)
        response = Response(AccountSerializer(user).data)
        response.data['csrf_token'] = get_token(request)
        response.data['session_token'] = session_token
        return response


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmptySerializer

    @extend_schema(summary='Revoke the current tab-scoped API session', responses={204: None})
    def post(self, request):
        request.auth.revoke()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountMeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user

    @extend_schema(summary='Retrieve the authenticated account profile')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary='Update account contact details; roles are read-only')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class AccountPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Retrieve the authenticated user’s personal preferences',
        responses={200: UserPreferencesSerializer},
    )
    def get(self, request):
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        return Response(UserPreferencesSerializer(preferences).data)

    @transaction.atomic
    @extend_schema(
        summary='Update the authenticated user’s personal preferences',
        request=UserPreferencesSerializer,
        responses={200: UserPreferencesSerializer},
    )
    def patch(self, request):
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        serializer = UserPreferencesSerializer(
            preferences,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AccountPreferencesResetView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    @extend_schema(
        summary='Reset the authenticated user’s personal preferences to defaults',
        request=None,
        responses={200: UserPreferencesSerializer},
    )
    def post(self, request):
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        preferences.theme = UserPreferences.Theme.SYSTEM
        preferences.locale = UserPreferences.Locale.ENGLISH
        preferences.density = UserPreferences.Density.COMFORTABLE
        preferences.reduced_motion = False
        preferences.save(update_fields=[
            'theme',
            'locale',
            'density',
            'reduced_motion',
            'updated_at',
        ])
        return Response(UserPreferencesSerializer(preferences).data)


class AccountActivityView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountActivitySerializer

    @extend_schema(summary='List the authenticated user’s saved properties and viewing requests')
    def get(self, request):
        viewing_requests = ViewingRequest.objects.none()
        profile_role = Profile.objects.filter(user_id=request.user.pk).values_list('role', flat=True).first()
        if profile_role != Profile.Role.BROKER:
            viewing_requests = (
                ViewingRequest.objects.filter(requester=request.user)
                .select_related('property')
                .order_by('-created_at')
            )
        activity = {
            'favorites': Favorite.objects.filter(user=request.user)
            .select_related('property')
            .order_by('-created_at'),
            'viewing_requests': viewing_requests,
        }
        serializer = self.get_serializer(instance=activity)
        return Response(serializer.data)
