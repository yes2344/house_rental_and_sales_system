from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.permissions import IsListingManager, IsViewingRequestManager
from properties.access import managed_properties
from viewings.models import ViewingRequest
from viewings.serializers import (
    ManagedViewingRequestSerializer,
    PublicViewingRequestCreateSerializer,
    PublicViewingRequestReceiptSerializer,
)


class PublicViewingRequestCreateView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_viewing_request'
    serializer_class = PublicViewingRequestCreateSerializer

    @extend_schema(
        summary='Submit a public property viewing request',
        description='Creates a pending request for a published available property without requiring an account.',
        responses={201: PublicViewingRequestReceiptSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        viewing_request = serializer.instance
        return Response(
            {
                'id': viewing_request.pk,
                'status': viewing_request.status,
                'created_at': viewing_request.created_at,
            },
            status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer):
        requester = self.request.user if self.request.user.is_authenticated else None
        serializer.save(requester=requester)


class ManagedViewingRequestListView(generics.ListAPIView):
    permission_classes = [IsListingManager]
    serializer_class = ManagedViewingRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'preferred_date', 'scheduled_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            ViewingRequest.objects.filter(property__in=managed_properties(self.request.user))
            .select_related('property')
            .order_by(*self.ordering)
        )

    @extend_schema(summary='List viewing requests for properties the user manages')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ManagedViewingRequestDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsViewingRequestManager]
    serializer_class = ManagedViewingRequestSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        return (
            ViewingRequest.objects.filter(property__in=managed_properties(self.request.user))
            .select_related('property')
        )

    @extend_schema(summary='Review a viewing request for a managed property')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary='Update request status, appointment schedule, and private agent notes')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
