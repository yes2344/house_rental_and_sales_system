import hashlib

from django.db import IntegrityError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import Profile
from accounts.permissions import (
    IsNotBrokerAccount,
    IsViewingRequestManager,
    has_management_permission,
)
from viewings.models import ViewingRequest
from viewings.serializers import (
    appointment_is_in_past,
    GuestViewingRequestDecisionSerializer,
    GuestViewingRequestStatusSerializer,
    CustomerViewingRequestSerializer,
    ManagedViewingRequestActionSerializer,
    ManagedViewingRequestSerializer,
    PublicViewingRequestCreateSerializer,
    PublicViewingRequestReceiptSerializer,
    ViewingRequestCancellationSerializer,
    ViewingRequestResponseSerializer,
)
from viewings.models import ViewingRequestEvent
from viewings.notifications import notify_viewing_request_event


class ActiveViewingRequestConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'You already have an active viewing request for this property.'
    default_code = 'active_viewing_request'


class PublicViewingRequestCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsNotBrokerAccount]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_viewing_request'
    serializer_class = PublicViewingRequestCreateSerializer

    @extend_schema(
        summary='Submit a public property viewing request',
        description='Creates a pending request for a published available property for the authenticated customer.',
        responses={201: PublicViewingRequestReceiptSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        property_obj = serializer.validated_data['property']
        if ViewingRequest.objects.filter(
            requester=request.user,
            property=property_obj,
            status__in=self.active_statuses,
        ).exists():
            raise ActiveViewingRequestConflict()
        try:
            with transaction.atomic():
                viewing_request = serializer.save(
                    requester=request.user,
                )
                event = ViewingRequestEvent.objects.create(
                    viewing_request=viewing_request,
                    actor=request.user,
                    event_type=ViewingRequestEvent.Type.SUBMITTED,
                    to_status=viewing_request.status,
                )
                notify_viewing_request_event(viewing_request, event, to_requester=False)
        except IntegrityError:
            if ViewingRequest.objects.filter(
                requester=request.user,
                property=property_obj,
                status__in=self.active_statuses,
            ).exists():
                raise ActiveViewingRequestConflict() from None
            raise
        response = Response(
            {
                'id': viewing_request.pk,
                'status': viewing_request.status,
                'created_at': viewing_request.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
        response['Cache-Control'] = 'no-store'
        return response

    active_statuses = [
        ViewingRequest.Status.PENDING,
        ViewingRequest.Status.PROPOSED,
        ViewingRequest.Status.CONFIRMED,
        ViewingRequest.Status.DECLINED,
    ]


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
            if (
                viewing_request.proposed_date is None
                or viewing_request.proposed_time is None
                or appointment_is_in_past(
                    viewing_request.proposed_date,
                    viewing_request.proposed_time,
                )
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
            event = ViewingRequestEvent.objects.create(
                viewing_request=viewing_request,
                event_type=event_type,
                from_status=old_status,
                to_status=viewing_request.status,
                proposed_date=viewing_request.proposed_date,
                proposed_time=viewing_request.proposed_time,
            )
            notify_viewing_request_event(viewing_request, event, to_requester=False)
        return Response(GuestViewingRequestStatusSerializer(viewing_request).data)


def manageable_viewing_requests(user):
    if has_management_permission(
        user,
        Profile.Permission.VIEWING_VIEW_ALL,
    ) or has_management_permission(user, Profile.Permission.VIEWING_MANAGE_ALL):
        return ViewingRequest.objects.all()

    scope = Q(pk__in=[])
    if has_management_permission(user, Profile.Permission.VIEWING_MANAGE_ASSIGNED):
        scope |= Q(property__assigned_brokers=user)
    return ViewingRequest.objects.filter(scope).distinct()


class CustomerViewingRequestListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsNotBrokerAccount]
    serializer_class = CustomerViewingRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'preferred_date', 'scheduled_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            ViewingRequest.objects.filter(requester=self.request.user)
            .select_related('property')
            .prefetch_related('events__actor')
            .order_by(*self.ordering)
        )


class CustomerViewingRequestDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsNotBrokerAccount]
    serializer_class = CustomerViewingRequestSerializer

    def get_queryset(self):
        return (
            ViewingRequest.objects.filter(requester=self.request.user)
            .select_related('property')
            .prefetch_related('events__actor')
        )


class CustomerViewingRequestResponseView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsNotBrokerAccount]
    serializer_class = ViewingRequestResponseSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        viewing_request = (
            ViewingRequest.objects.select_for_update()
            .filter(pk=kwargs['pk'], requester=request.user)
            .select_related('property')
            .first()
        )
        if viewing_request is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if viewing_request.status != ViewingRequest.Status.PROPOSED:
            return Response(
                {'detail': 'There is no pending appointment proposal to decide.'},
                status=status.HTTP_409_CONFLICT,
            )
        if (
            viewing_request.proposed_date is None
            or viewing_request.proposed_time is None
            or appointment_is_in_past(viewing_request.proposed_date, viewing_request.proposed_time)
        ):
            return Response(
                {'detail': 'This appointment proposal has expired. Contact the property manager.'},
                status=status.HTTP_409_CONFLICT,
            )

        decision = serializer.validated_data['decision']
        previous_status = viewing_request.status
        if decision == 'accept':
            viewing_request.status = ViewingRequest.Status.CONFIRMED
            viewing_request.scheduled_date = viewing_request.proposed_date
            viewing_request.scheduled_time = viewing_request.proposed_time
            event_type = ViewingRequestEvent.Type.PROPOSAL_ACCEPTED
        else:
            viewing_request.status = ViewingRequest.Status.DECLINED
            event_type = ViewingRequestEvent.Type.PROPOSAL_DECLINED
        viewing_request.guest_responded_at = timezone.now()
        viewing_request.save(update_fields=[
            'status', 'scheduled_date', 'scheduled_time', 'guest_responded_at',
        ])
        event = ViewingRequestEvent.objects.create(
            viewing_request=viewing_request,
            actor=request.user,
            event_type=event_type,
            from_status=previous_status,
            to_status=viewing_request.status,
            proposed_date=viewing_request.proposed_date,
            proposed_time=viewing_request.proposed_time,
            message=serializer.validated_data.get('message', ''),
        )
        notify_viewing_request_event(viewing_request, event, to_requester=False)
        return Response(CustomerViewingRequestSerializer(viewing_request).data)


class CustomerViewingRequestCancelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsNotBrokerAccount]
    serializer_class = ViewingRequestCancellationSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        viewing_request = (
            ViewingRequest.objects.select_for_update()
            .filter(pk=kwargs['pk'], requester=request.user)
            .select_related('property')
            .first()
        )
        if viewing_request is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if viewing_request.status not in PublicViewingRequestCreateView.active_statuses:
            return Response(
                {'detail': 'This viewing request is already closed.'},
                status=status.HTTP_409_CONFLICT,
            )

        previous_status = viewing_request.status
        viewing_request.status = ViewingRequest.Status.CANCELLED
        viewing_request.save(update_fields=['status'])
        event = ViewingRequestEvent.objects.create(
            viewing_request=viewing_request,
            actor=request.user,
            event_type=ViewingRequestEvent.Type.CANCELLED,
            from_status=previous_status,
            to_status=viewing_request.status,
            message=serializer.validated_data.get('message', ''),
        )
        notify_viewing_request_event(viewing_request, event, to_requester=False)
        return Response(CustomerViewingRequestSerializer(viewing_request).data)


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
        previous_event_id = viewing_request.events.order_by('-pk').values_list('pk', flat=True).first()
        updated = serializer.save()
        event = updated.events.exclude(pk=previous_event_id).order_by('-pk').first()
        if event:
            notify_viewing_request_event(updated, event, to_requester=True)

    @extend_schema(summary='Review a viewing request for a managed property')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary='Update request status, appointment schedule, and private agent notes')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ManagedViewingRequestActionView(generics.GenericAPIView):
    permission_classes = [IsViewingRequestManager]
    serializer_class = ManagedViewingRequestActionSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        viewing_request = (
            manageable_viewing_requests(request.user)
            .select_for_update()
            .select_related('property')
            .filter(pk=kwargs['pk'])
            .first()
        )
        if viewing_request is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        action = serializer.validated_data['action']
        previous_status = viewing_request.status
        if action == 'confirm_requested':
            if previous_status not in (ViewingRequest.Status.PENDING, ViewingRequest.Status.DECLINED):
                return Response({'detail': 'This request cannot be confirmed in its current state.'}, status=409)
            if viewing_request.preferred_time is None or appointment_is_in_past(
                viewing_request.preferred_date,
                viewing_request.preferred_time,
            ):
                return Response({'detail': 'The requested appointment time is unavailable or has passed.'}, status=409)
            viewing_request.status = ViewingRequest.Status.CONFIRMED
            viewing_request.scheduled_date = viewing_request.preferred_date
            viewing_request.scheduled_time = viewing_request.preferred_time
            event_type = ViewingRequestEvent.Type.REQUEST_CONFIRMED
        elif action == 'cancel':
            if previous_status not in PublicViewingRequestCreateView.active_statuses:
                return Response({'detail': 'This viewing request is already closed.'}, status=409)
            viewing_request.status = ViewingRequest.Status.CANCELLED
            event_type = ViewingRequestEvent.Type.CANCELLED
        else:
            if previous_status != ViewingRequest.Status.CONFIRMED:
                return Response({'detail': 'Only a confirmed viewing can be completed.'}, status=409)
            if viewing_request.scheduled_date is None or viewing_request.scheduled_time is None:
                return Response({'detail': 'A confirmed viewing needs a scheduled date and time.'}, status=409)
            if not appointment_is_in_past(viewing_request.scheduled_date, viewing_request.scheduled_time):
                return Response({'detail': 'A viewing cannot be completed before its scheduled time.'}, status=409)
            viewing_request.status = ViewingRequest.Status.COMPLETED
            event_type = ViewingRequestEvent.Type.COMPLETED

        viewing_request.save(update_fields=['status', 'scheduled_date', 'scheduled_time'])
        event = ViewingRequestEvent.objects.create(
            viewing_request=viewing_request,
            actor=request.user,
            event_type=event_type,
            from_status=previous_status,
            to_status=viewing_request.status,
            proposed_date=viewing_request.scheduled_date,
            proposed_time=viewing_request.scheduled_time,
            message=serializer.validated_data.get('message', ''),
        )
        notify_viewing_request_event(viewing_request, event, to_requester=True)
        return Response(ManagedViewingRequestSerializer(viewing_request).data)
