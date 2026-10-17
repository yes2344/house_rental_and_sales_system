import calendar
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from accounts.permissions import HasManagementPermission, has_management_permission
from admin.audit import record_admin_action
from owner_announcements.models import (
    InAppNotification,
    OwnerAnnouncement,
    OwnerAnnouncementAgreement,
    OwnerAnnouncementEvent,
)
from owner_announcements.serializers import (
    OwnerAnnouncementAssignmentSerializer,
    InAppNotificationSerializer,
    OwnerAnnouncementReviewerSerializer,
    OwnerAnnouncementReviewSerializer,
    OwnerPropertySubmissionSerializer,
)
from properties.access import broker_city_location_ids
from properties.models import Property, PropertyImage
from properties.serializers import PropertyImageManagementSerializer


class IsPropertySubmitter(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.is_active:
            return False
        return Profile.objects.filter(
            user=request.user,
            role__in=(Profile.Role.CUSTOMER, Profile.Role.OWNER),
        ).exists()

    def has_object_permission(self, request, view, obj):
        announcement = getattr(obj, 'owner_announcement', obj)
        return announcement.submitter_id == request.user.pk


class OwnerSubmissionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsPropertySubmitter]
    serializer_class = OwnerPropertySubmissionSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Property.objects.filter(
            owner_announcement__submitter=self.request.user,
        ).select_related(
            'owner_announcement',
            'administrative_location',
        ).prefetch_related('amenities', 'images', 'owner_announcement__events')

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()


class OwnerSubmissionDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsPropertySubmitter]
    serializer_class = OwnerPropertySubmissionSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        return Property.objects.filter(
            owner_announcement__submitter=self.request.user,
        ).select_related(
            'owner_announcement',
            'administrative_location',
        ).prefetch_related('amenities', 'images', 'owner_announcement__events')

    @transaction.atomic
    def perform_update(self, serializer):
        announcement = OwnerAnnouncement.objects.select_for_update().get(
            property_id=serializer.instance.pk,
            submitter=self.request.user,
        )
        property_obj = Property.objects.select_for_update().get(pk=serializer.instance.pk)
        if announcement.status != OwnerAnnouncement.Status.CORRECTIONS_REQUESTED:
            raise ValidationError({'detail': 'Only submissions with requested corrections can be edited.'})
        serializer.instance = property_obj
        serializer.save()


class OwnerSubmissionImageListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsPropertySubmitter]
    serializer_class = PropertyImageManagementSerializer

    def get_property(self):
        return get_object_or_404(
            Property.objects.select_related('owner_announcement'),
            pk=self.kwargs['submission_id'],
            owner_announcement__submitter=self.request.user,
            owner_announcement__status__in=(
                OwnerAnnouncement.Status.PENDING_REVIEW,
                OwnerAnnouncement.Status.CORRECTIONS_REQUESTED,
            ),
        )

    def get_queryset(self):
        return PropertyImage.objects.filter(property=self.get_property()).select_related('property')

    def perform_create(self, serializer):
        serializer.save(property=self.get_property())


def _review_queryset_for_user(user):
    queryset = OwnerAnnouncement.objects.select_related(
        'submitter',
        'reviewed_by',
        'property',
        'property__administrative_location',
    ).prefetch_related(
        'property__images',
        'property__amenities',
        'events__actor',
        'agreements',
    )
    if user.is_superuser or (
        user.is_staff
        and Profile.objects.filter(user=user, role=Profile.Role.ADMINISTRATOR).exists()
    ):
        return queryset
    if Profile.objects.filter(user=user, role=Profile.Role.BROKER).exists():
        if has_management_permission(user, Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED):
            return queryset.filter(assigned_reviewer=user)
    return queryset.none()


class OwnerAnnouncementReviewListView(generics.ListAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = (
        Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW,
        Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED,
    )
    serializer_class = OwnerAnnouncementReviewSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['submitted_at', 'updated_at']
    ordering = ['-submitted_at']

    def get_queryset(self):
        queryset = _review_queryset_for_user(self.request.user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            if status_filter not in OwnerAnnouncement.Status.values:
                raise ValidationError({'status': 'Choose a valid submission status.'})
            queryset = queryset.filter(status=status_filter)
        return queryset


class OwnerAnnouncementReviewDetailView(generics.RetrieveAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = (
        Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW,
        Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED,
    )
    serializer_class = OwnerAnnouncementReviewSerializer
    queryset = OwnerAnnouncement.objects.none()

    def get_queryset(self):
        return _review_queryset_for_user(self.request.user)


class OwnerAnnouncementReviewerListView(generics.ListAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.OWNER_ANNOUNCEMENTS_ASSIGN
    serializer_class = OwnerAnnouncementReviewerSerializer
    pagination_class = None

    def get_queryset(self):
        candidates = get_user_model().objects.filter(
            is_active=True,
            profile__role=Profile.Role.BROKER,
            profile__broker_approved=True,
        ).select_related('profile').order_by('username')
        return [
            user
            for user in candidates
            if has_management_permission(
                user,
                Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED,
            )
        ]


class OwnerAnnouncementAssignmentView(APIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.OWNER_ANNOUNCEMENTS_ASSIGN

    @transaction.atomic
    def post(self, request, pk):
        announcement = get_object_or_404(
            OwnerAnnouncement.objects.select_for_update(of=('self',)).select_related('assigned_reviewer'),
            pk=pk,
        )
        if announcement.status not in (
            OwnerAnnouncement.Status.PENDING_REVIEW,
            OwnerAnnouncement.Status.CORRECTIONS_REQUESTED,
        ):
            raise ValidationError({'status': 'Only submissions awaiting review can be assigned.'})

        serializer = OwnerAnnouncementAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewer_id = serializer.validated_data['assigned_reviewer_id']
        reviewer = None
        if reviewer_id is not None:
            reviewer = get_object_or_404(
                get_user_model().objects.select_related('profile').filter(
                    is_active=True,
                    profile__role=Profile.Role.BROKER,
                    profile__broker_approved=True,
                ),
                pk=reviewer_id,
            )
            if reviewer.pk == announcement.submitter_id:
                raise ValidationError({
                    'assigned_reviewer_id': 'A submitter cannot review their own property submission.',
                })
            if not has_management_permission(
                reviewer,
                Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED,
            ):
                raise ValidationError({
                    'assigned_reviewer_id': 'Choose an active agent with explicit submission-review permission.',
                })

        previous_reviewer = announcement.assigned_reviewer
        if previous_reviewer == reviewer:
            return Response(OwnerAnnouncementReviewSerializer(
                announcement,
                context={'request': request},
            ).data)

        announcement.assigned_reviewer = reviewer
        announcement.save(update_fields=['assigned_reviewer', 'updated_at'])
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=request.user,
            event_type=(
                OwnerAnnouncementEvent.Type.ASSIGNED
                if reviewer
                else OwnerAnnouncementEvent.Type.UNASSIGNED
            ),
            details={
                'previous_reviewer_id': previous_reviewer.pk if previous_reviewer else None,
                'assigned_reviewer_id': reviewer.pk if reviewer else None,
                'assigned_reviewer_name': (
                    ' '.join(part for part in (reviewer.first_name, reviewer.last_name) if part)
                    or reviewer.username
                    if reviewer
                    else None
                ),
            },
        )
        record_admin_action(
            request.user,
            action='owner_submission_reviewer_assigned',
            object_type='owner_announcement',
            object_id=announcement.pk,
            changes={
                'assigned_reviewer_id': {
                    'from': previous_reviewer.pk if previous_reviewer else None,
                    'to': reviewer.pk if reviewer else None,
                },
            },
        )
        return Response(OwnerAnnouncementReviewSerializer(
            announcement,
            context={'request': request},
        ).data)


class OwnerAnnouncementDecisionView(APIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = (
        Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW,
        Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED,
    )

    @transaction.atomic
    def post(self, request, pk):
        announcement = get_object_or_404(
            _review_queryset_for_user(request.user).select_for_update(of=('self',)),
            pk=pk,
        )
        if announcement.submitter_id == request.user.pk:
            raise ValidationError({'detail': 'You cannot review your own submission.'})
        if announcement.status not in (
            OwnerAnnouncement.Status.PENDING_REVIEW,
            OwnerAnnouncement.Status.CORRECTIONS_REQUESTED,
        ):
            raise ValidationError({'status': 'This submission is no longer awaiting review.'})

        action = request.data.get('action')
        feedback = str(request.data.get('feedback', '')).strip()
        if action not in ('approve', 'reject', 'request_corrections'):
            raise ValidationError({'action': 'Choose approve, reject, or request_corrections.'})
        if action in ('reject', 'request_corrections') and not feedback:
            raise ValidationError({'feedback': 'An explanation is required for this decision.'})

        property_obj = Property.objects.select_for_update().get(pk=announcement.property_id)
        previous_status = announcement.status
        now = timezone.now()
        details = {'feedback': feedback} if feedback else {}

        if action == 'approve':
            if property_obj.status not in (Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE):
                raise ValidationError({'status': 'Only available properties can be approved.'})
            start_date = _parse_date(request.data.get('agreement_start_date'), 'agreement_start_date')
            duration = request.data.get('agreement_duration_months')
            try:
                duration = int(duration)
            except (TypeError, ValueError) as exc:
                raise ValidationError({'agreement_duration_months': 'Enter a valid agreement duration.'}) from exc
            if not 1 <= duration <= 120:
                raise ValidationError({'agreement_duration_months': 'Duration must be between 1 and 120 months.'})
            terms = str(request.data.get('agreement_terms', '')).strip()
            if not terms:
                raise ValidationError({'agreement_terms': 'Agreement terms are required before publication.'})
            end_date = _add_months(start_date, duration)
            announcement.agreements.filter(
                status=OwnerAnnouncementAgreement.Status.ACTIVE,
            ).update(status=OwnerAnnouncementAgreement.Status.SUPERSEDED)
            OwnerAnnouncementAgreement.objects.create(
                announcement=announcement,
                start_date=start_date,
                end_date=end_date,
                duration_months=duration,
                terms=terms,
                public_contact_visible=False,
                status=OwnerAnnouncementAgreement.Status.ACTIVE,
                approved_by=request.user,
            )
            next_status = OwnerAnnouncement.Status.APPROVED
            property_obj.publication_status = Property.PublicationStatus.PUBLISHED
            property_obj.moderation_note = ''
            property_obj.contact_publicly_visible = False
            details.update({
                'agreement_start_date': start_date.isoformat(),
                'agreement_end_date': end_date.isoformat(),
                'agreement_duration_months': duration,
                'public_contact_visible': False,
            })
        elif action == 'reject':
            next_status = OwnerAnnouncement.Status.REJECTED
            property_obj.publication_status = Property.PublicationStatus.REJECTED
            property_obj.moderation_note = feedback
        else:
            next_status = OwnerAnnouncement.Status.CORRECTIONS_REQUESTED
            property_obj.publication_status = Property.PublicationStatus.PENDING_REVIEW
            property_obj.moderation_note = feedback

        announcement.status = next_status
        announcement.broker_feedback = feedback
        announcement.reviewed_by = request.user
        announcement.reviewed_at = now
        announcement.save(update_fields=[
            'status',
            'broker_feedback',
            'reviewed_by',
            'reviewed_at',
            'updated_at',
        ])
        property_obj.save(update_fields=[
            'publication_status',
            'moderation_note',
            'contact_publicly_visible',
            'updated_at',
        ])
        event = OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=request.user,
            event_type={
                'approve': OwnerAnnouncementEvent.Type.APPROVED,
                'reject': OwnerAnnouncementEvent.Type.REJECTED,
                'request_corrections': OwnerAnnouncementEvent.Type.CORRECTIONS_REQUESTED,
            }[action],
            from_status=previous_status,
            to_status=next_status,
            details=details,
        )
        InAppNotification.objects.create(
            recipient=announcement.submitter,
            announcement=announcement,
            notification_type=f'owner_submission_{next_status}',
            message=f'Your property submission "{property_obj.title}" is {next_status.replace("_", " ")}.'
            + (f' {feedback}' if feedback else ''),
            idempotency_key=f'owner-submission:{announcement.pk}:event:{event.pk}',
        )
        record_admin_action(
            request.user,
            action='owner_submission_reviewed',
            object_type='owner_announcement',
            object_id=announcement.pk,
            changes={
                'status': {'from': previous_status, 'to': next_status},
                **({'feedback': feedback} if feedback else {}),
            },
        )
        return Response(
            OwnerAnnouncementReviewSerializer(announcement, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


def _parse_date(value, field):
    if not isinstance(value, str):
        raise ValidationError({field: 'Enter a valid date.'})
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({field: 'Enter a valid date.'}) from exc


def _add_months(start_date, months):
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class InAppNotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InAppNotificationSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return InAppNotification.objects.filter(recipient=self.request.user).select_related('announcement')


class InAppNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(InAppNotification, pk=pk, recipient=request.user)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=['read_at'])
        return Response(InAppNotificationSerializer(notification).data)
