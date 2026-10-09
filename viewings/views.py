import hashlib
import secrets

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import Profile
from accounts.permissions import (
    IsViewingRequestManager,
    has_management_permission,
    is_platform_administrator,
)
from viewings.models import ViewingRequest
from viewings.serializers import (
    appointment_is_in_past,
    GuestViewingRequestDecisionSerializer,
    GuestViewingRequestStatusSerializer,
    ManagedViewingRequestSerializer,
    PublicViewingRequestCreateSerializer,
    PublicViewingRequestReceiptSerializer,
)
from viewings.models import ViewingRequestEvent


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
        self.receipt_token = None
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        viewing_request = serializer.instance
        response = Response(
            {
                'id': viewing_request.pk,
                'status': viewing_request.status,
                'created_at': viewing_request.created_at,
                'receipt_token': self.receipt_token,
            },
            status=status.HTTP_201_CREATED,
        )
        response['Cache-Control'] = 'no-store'
        return response

    def perform_create(self, serializer):
        requester = self.request.user if self.request.user.is_authenticated else None
        self.receipt_token = secrets.token_urlsafe(32)
        with transaction.atomic():
            viewing_request = serializer.save(
                requester=requester,
                receipt_token_digest=hashlib.sha256(self.receipt_token.encode()).hexdigest(),
            )
            ViewingRequestEvent.objects.create(
                viewing_request=viewing_request,
                actor=requester,
                event_type=ViewingRequestEvent.Type.SUBMITTED,
                to_status=viewing_request.status,
            )


class PrivateGuestReceiptView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_viewing_receipt'

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'no-referrer'
        return response

    def get_viewing_request(self, request, *, lock=False):
        raw_token = request.headers.get('X-Viewing-Receipt', '')
        if not raw_token or len(raw_token) > 200:
            return None
        digest = hashlib.sha256(raw_token.encode()).hexdigest()
        queryset = ViewingRequest.objects.select_related('property')
        if lock:
            queryset = queryset.select_for_update()
        return queryset.filter(receipt_token_digest=digest).first()

    @extend_schema(
        summary='Retrieve a viewing-request status using its private receipt token',
        responses={200: GuestViewingRequestStatusSerializer},
    )
    def get(self, request):
        viewing_request = self.get_viewing_request(request)
        if viewing_request is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(GuestViewingRequestStatusSerializer(viewing_request).data)

    @extend_schema(
        summary='Accept or decline a proposed viewing appointment',
        request=GuestViewingRequestDecisionSerializer,
        responses={200: GuestViewingRequestStatusSerializer},
    )
    def post(self, request):
        serializer = GuestViewingRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            viewing_request = self.get_viewing_request(request, lock=True)
            if viewing_request is None:
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            if viewing_request.status != ViewingRequest.Status.PROPOSED:
                return Response(
                    {'detail': 'There is no pending appointment proposal to decide.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if appointment_is_in_past(
                viewing_request.proposed_date,
                viewing_request.proposed_time,
            ):
                return Response(
                    {'detail': 'This appointment proposal has expired. Contact the property manager.'},
                    status=status.HTTP_409_CONFLICT,
                )

            decision = serializer.validated_data['decision']
            old_status = viewing_request.status
            if decision == 'accept':
                viewing_request.status = ViewingRequest.Status.CONFIRMED
                viewing_request.scheduled_date = viewing_request.proposed_date
                viewing_request.scheduled_time = viewing_request.proposed_time
                event_type = ViewingRequestEvent.Type.PROPOSAL_ACCEPTED
            else:
                viewing_request.status = ViewingRequest.Status.DECLINED
                event_type = ViewingRequestEvent.Type.PROPOSAL_DECLINED
            viewing_request.guest_responded_at = timezone.now()
            viewing_request.save(
                update_fields=[
                    'status',
                    'scheduled_date',
                    'scheduled_time',
                    'guest_responded_at',
                ]
            )
            ViewingRequestEvent.objects.create(
                viewing_request=viewing_request,
                event_type=event_type,
                from_status=old_status,
                to_status=viewing_request.status,
                proposed_date=viewing_request.proposed_date,
                proposed_time=viewing_request.proposed_time,
            )
        return Response(GuestViewingRequestStatusSerializer(viewing_request).data)


def manageable_viewing_requests(user):
    if is_platform_administrator(user) or has_management_permission(
        user,
        Profile.Permission.VIEWING_VIEW_ALL,
    ) or has_management_permission(user, Profile.Permission.VIEWING_MANAGE_ALL):
        return ViewingRequest.objects.all()

    scope = Q(pk__in=[])
    if has_management_permission(user, Profile.Permission.VIEWING_MANAGE_ASSIGNED):
        scope |= Q(property__assigned_brokers=user)
    return ViewingRequest.objects.filter(scope).distinct()


class ManagedViewingRequestListView(generics.ListAPIView):
    permission_classes = [IsViewingRequestManager]
    serializer_class = ManagedViewingRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'preferred_date', 'scheduled_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            manageable_viewing_requests(self.request.user)
            .select_related('property')
            .prefetch_related('events__actor')
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
            manageable_viewing_requests(self.request.user)
            .select_related('property')
            .prefetch_related('events__actor')
        )

    @transaction.atomic
    def perform_update(self, serializer):
        viewing_request = (
            self.get_queryset()
            .select_for_update()
            .get(pk=serializer.instance.pk)
        )
        serializer.instance = viewing_request
        serializer.save()

    @extend_schema(summary='Review a viewing request for a managed property')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary='Update request status, appointment schedule, and private agent notes')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
