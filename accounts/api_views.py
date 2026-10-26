import logging

from django.contrib.auth import get_user_model
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

from accounts.models import EmailVerificationToken, Profile, TabSessionToken, UserPreferences
from accounts.email_messages import (
    AccountEmailDeliveryError,
    send_password_reset_email,
    send_verification_email,
)
from accounts.serializers import (
    AccountActivitySerializer,
    AccountSerializer,
    AgentFirstLoginPasswordSerializer,
    AgentFirstLoginProfileSerializer,
    CsrfTokenSerializer,
    DelegatedInvitationAcceptSerializer,
    EmptySerializer,
    EmailAddressSerializer,
    EmailVerificationSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    RegistrationSerializer,
    UserPreferencesSerializer,
)
from favorites.models import Favorite
from viewings.models import ViewingRequest

logger = logging.getLogger(__name__)


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
        try:
            user = serializer.save()
        except AccountEmailDeliveryError:
            return Response(
                {'detail': 'The verification email could not be sent. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(AccountSerializer(user).data, status=status.HTTP_201_CREATED)


class EmailVerificationView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'account_email_verification'
    serializer_class = EmailVerificationSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Your email address is verified. You can now sign in.'},
            status=status.HTTP_200_OK,
        )


class ResendVerificationEmailView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'account_email_resend'
    serializer_class = EmailAddressSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.filter(
            email__iexact=serializer.validated_data['email'],
            is_active=False,
            is_staff=False,
            is_superuser=False,
            profile__role=Profile.Role.CUSTOMER,
            email_verification_tokens__isnull=False,
        ).first()
        if user:
            _, token = EmailVerificationToken.issue(user)
            try:
                send_verification_email(user, token)
            except AccountEmailDeliveryError:
                logger.warning('Verification email resend failed.')
        return Response(
            {'detail': 'If an unverified account matches that email, a verification message will be sent.'},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetRequestView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'account_password_reset'
    serializer_class = EmailAddressSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.filter(
            email__iexact=serializer.validated_data['email'],
            is_active=True,
        ).first()
        if user:
            try:
                send_password_reset_email(user)
            except AccountEmailDeliveryError:
                logger.warning('Password reset email delivery failed.')
        return Response(
            {'detail': 'If an account matches that email, password reset instructions will be sent.'},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'account_password_reset'
    serializer_class = PasswordResetSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Your password has been changed. You can now sign in.'},
            status=status.HTTP_200_OK,
        )


class DelegatedInvitationAcceptView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'delegated_invitation_accept'
    serializer_class = DelegatedInvitationAcceptSerializer

    @extend_schema(
        summary='Accept an owner-issued administrator or agent invitation',
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


class AgentFirstLoginPasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AgentFirstLoginPasswordSerializer

    @transaction.atomic
    @extend_schema(
        summary='Set a provisioned agent’s permanent password and optional username',
        request=AgentFirstLoginPasswordSerializer,
        responses={200: AccountSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AccountSerializer(user).data)


class AgentFirstLoginProfileView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AgentFirstLoginProfileSerializer

    @transaction.atomic
    @extend_schema(
        summary='Complete a provisioned agent’s contact profile and activate agent permissions',
        request=AgentFirstLoginProfileSerializer,
        responses={200: AccountSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AccountSerializer(user).data)


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
        if profile_role != Profile.Role.AGENT:
            viewing_requests = (
                ViewingRequest.objects.filter(
                    requester=request.user,
                    requester_deleted_at__isnull=True,
                )
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
