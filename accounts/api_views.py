from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.serializers import (
    AccountActivitySerializer,
    AccountSerializer,
    CsrfTokenSerializer,
    EmptySerializer,
    LoginResponseSerializer,
    LoginSerializer,
    RegistrationSerializer,
)
from favorites.models import Favorite
from viewings.models import ViewingRequest


class CsrfTokenView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = CsrfTokenSerializer

    @extend_schema(summary='Get a CSRF token for session-authenticated browser requests')
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
        summary='Start a session',
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        response = Response(AccountSerializer(user).data)
        response.data['csrf_token'] = get_token(request)
        return response


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmptySerializer

    @extend_schema(summary='End the current session', responses={204: None})
    def post(self, request):
        logout(request)
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


class AccountActivityView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountActivitySerializer

    @extend_schema(summary='List the authenticated user’s saved properties and viewing requests')
    def get(self, request):
        activity = {
            'favorites': Favorite.objects.filter(user=request.user)
            .select_related('property')
            .order_by('-created_at'),
            'viewing_requests': ViewingRequest.objects.filter(requester=request.user)
            .select_related('property')
            .order_by('-created_at'),
        }
        serializer = self.get_serializer(instance=activity)
        return Response(serializer.data)
