from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import timedelta

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
    BrokerAnnouncementDecisionSerializer,
    BrokerAnnouncementSerializer,
    InAppNotificationSerializer,
    OwnerAnnouncementSerializer,
    OwnerAnnouncementSubmissionSerializer,
)
from properties.models import Property, PropertyImage
from properties.serializers import PropertyImageManagementSerializer


User = get_user_model()
BROKER_REVIEW_PERMISSION = Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW


def notify_user(user, announcement, notification_type, message, idempotency_key):
    return InAppNotification.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            'recipient': user,
            'announcement': announcement,
            'notification_type': notification_type,
            'message': message,
        },
    )[0]


def broker_recipients():
    recipients = {}
    for profile in Profile.objects.select_related('user').filter(user__is_active=True):
        if has_management_permission(profile.user, BROKER_REVIEW_PERMISSION):
            recipients[profile.user_id] = profile.user
    return list(recipients.values())


def notify_brokers(announcement, notification_type, message, suffix):
    for recipient in broker_recipients():
        notify_user(
            recipient,
            announcement,
            notification_type,
            message,
            f'announcement:{announcement.pk}:{suffix}:user:{recipient.pk}',
        )


class OwnerAnnouncementListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnerAnnouncementSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['submitted_at', 'updated_at']
    ordering = ['-submitted_at']

    def get_queryset(self):
        return (
            OwnerAnnouncement.objects.filter(submitter=self.request.user)
            .select_related('property', 'property__administrative_location')
            .prefetch_related('property__images', 'agreements', 'events')
            .order_by(*self.ordering)
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OwnerAnnouncementSubmissionSerializer
        return OwnerAnnouncementSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        announcement = serializer.save()
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=request.user,
            event_type=OwnerAnnouncementEvent.Type.SUBMITTED,
            to_status=announcement.status,
        )
        notify_user(
            request.user,
            announcement,
            'announcement_submitted',
            'Your property announcement was received and is pending broker review.',
            f'announcement:{announcement.pk}:submitted:owner:{request.user.pk}',
        )
        notify_brokers(
            announcement,
            'announcement_submitted',
            f'New owner announcement awaiting review: {announcement.property.title}.',
            'submitted',
        )
        return Response(
            OwnerAnnouncementSerializer(
                announcement,
                context={'request': request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class OwnerAnnouncementDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        return (
            OwnerAnnouncement.objects.filter(submitter=self.request.user)
            .select_related('property', 'property__administrative_location')
            .prefetch_related('property__images', 'agreements', 'events')
        )

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return OwnerAnnouncementSubmissionSerializer
        return OwnerAnnouncementSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        announcement = self.get_object()
        if announcement.status in (
            OwnerAnnouncement.Status.SUSPENDED,
            OwnerAnnouncement.Status.EXPIRED,
            OwnerAnnouncement.Status.WITHDRAWN,
        ):
            raise ValidationError({'status': 'This announcement can no longer be edited.'})
        serializer = self.get_serializer(
            announcement,
            data=request.data,
            partial=partial,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        notify_brokers(
            updated,
            'announcement_resubmitted',
            f'Owner updated and resubmitted property for review: {updated.property.title}.',
            f'resubmitted:{updated.updated_at.isoformat()}',
        )
        return Response(
            OwnerAnnouncementSerializer(updated, context={'request': request}).data,
        )


class OwnerAnnouncementImageListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyImageManagementSerializer

    def get_announcement(self):
        return get_object_or_404(
            OwnerAnnouncement.objects.select_related('property'),
            pk=self.kwargs['announcement_id'],
            submitter=self.request.user,
        )

    def get_queryset(self):
        return PropertyImage.objects.filter(property=self.get_announcement().property)

    @transaction.atomic
    def perform_create(self, serializer):
        announcement = self.get_announcement()
        if announcement.status in (
            OwnerAnnouncement.Status.SUSPENDED,
            OwnerAnnouncement.Status.EXPIRED,
            OwnerAnnouncement.Status.WITHDRAWN,
        ):
            raise ValidationError({'status': 'Images cannot be changed for this announcement.'})
        if announcement.property.images.count() >= 10:
            raise ValidationError({'image': 'A property can have at most 10 images.'})
        image = serializer.save(property=announcement.property)
        previous_status = announcement.status
        if announcement.status == OwnerAnnouncement.Status.APPROVED:
            announcement.status = OwnerAnnouncement.Status.PENDING_REVIEW
            announcement.broker_feedback = ''
            announcement.reviewed_by = None
            announcement.reviewed_at = None
            announcement.property.publication_status = Property.PublicationStatus.PENDING_REVIEW
            announcement.property.save(update_fields=['publication_status', 'updated_at'])
            announcement.save(update_fields=['status', 'broker_feedback', 'reviewed_by', 'reviewed_at', 'updated_at'])
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=self.request.user,
            event_type=OwnerAnnouncementEvent.Type.EDITED,
            from_status=previous_status,
            to_status=announcement.status,
            details={
                'public_listing_hidden_until_review': previous_status == OwnerAnnouncement.Status.APPROVED,
                'image_added': image.pk,
            },
        )
        notify_brokers(
            announcement,
            'announcement_updated',
            f'The owner updated photos for {announcement.property.title}.',
            f'image-added:{image.pk}',
        )


class OwnerAnnouncementImageDetailView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyImageManagementSerializer
    lookup_url_kwarg = 'image_id'

    def get_queryset(self):
        return PropertyImage.objects.filter(
            property__owner_announcement__submitter=self.request.user,
            property__owner_announcement__pk=self.kwargs['announcement_id'],
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        announcement = instance.property.owner_announcement
        if announcement.status in (
            OwnerAnnouncement.Status.SUSPENDED,
            OwnerAnnouncement.Status.EXPIRED,
            OwnerAnnouncement.Status.WITHDRAWN,
        ):
            raise ValidationError({'status': 'Images cannot be changed for this announcement.'})
        was_approved = announcement.status == OwnerAnnouncement.Status.APPROVED
        previous_status = announcement.status
        image_id = instance.pk
        instance.image.delete(save=False)
        instance.delete()
        if was_approved:
            announcement.status = OwnerAnnouncement.Status.PENDING_REVIEW
            announcement.broker_feedback = ''
            announcement.reviewed_by = None
            announcement.reviewed_at = None
            announcement.property.publication_status = Property.PublicationStatus.PENDING_REVIEW
            announcement.property.save(update_fields=['publication_status', 'updated_at'])
            announcement.save(update_fields=['status', 'broker_feedback', 'reviewed_by', 'reviewed_at', 'updated_at'])
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=self.request.user,
            event_type=OwnerAnnouncementEvent.Type.EDITED,
            from_status=previous_status,
            to_status=announcement.status,
            details={
                'public_listing_hidden_until_review': was_approved,
                'image_removed': image_id,
            },
        )
        notify_brokers(
            announcement,
            'announcement_updated',
            f'The owner updated photos for {announcement.property.title}.',
            f'image-removed:{image_id}',
        )


class OwnerAnnouncementRenewalView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        announcement = get_object_or_404(
            OwnerAnnouncement.objects.select_for_update().select_related('property'),
            pk=pk,
            submitter=request.user,
        )
        if announcement.status not in (
            OwnerAnnouncement.Status.APPROVED,
            OwnerAnnouncement.Status.EXPIRED,
        ):
            raise ValidationError({'status': 'Only approved or expired announcements can request renewal.'})
        if announcement.renewal_requested_at is not None:
            return Response(OwnerAnnouncementSerializer(announcement, context={'request': request}).data)
        announcement.renewal_requested_at = timezone.now()
        announcement.save(update_fields=['renewal_requested_at', 'updated_at'])
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=request.user,
            event_type=OwnerAnnouncementEvent.Type.RENEWAL_REQUESTED,
            from_status=announcement.status,
            to_status=announcement.status,
        )
        notify_user(
            request.user,
            announcement,
            'renewal_requested',
            'Your renewal request was sent to the brokerage.',
            f'announcement:{announcement.pk}:renewal:{announcement.renewal_requested_at.isoformat()}:owner',
        )
        notify_brokers(
            announcement,
            'renewal_requested',
            f'Renewal requested for {announcement.property.title}.',
            f'renewal:{announcement.renewal_requested_at.isoformat()}',
        )
        return Response(OwnerAnnouncementSerializer(announcement, context={'request': request}).data)


class OwnerAnnouncementWithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        announcement = get_object_or_404(
            OwnerAnnouncement.objects.select_for_update().select_related('property'),
            pk=pk,
            submitter=request.user,
        )
        if announcement.status in (OwnerAnnouncement.Status.EXPIRED, OwnerAnnouncement.Status.WITHDRAWN):
            raise ValidationError({'status': 'This announcement is already closed.'})
        before = announcement.status
        announcement.status = OwnerAnnouncement.Status.WITHDRAWN
        announcement.reviewed_at = timezone.now()
        announcement.reviewed_by = request.user
        announcement.property.publication_status = Property.PublicationStatus.WITHDRAWN
        announcement.property.save(update_fields=['publication_status', 'updated_at'])
        announcement.save(update_fields=['status', 'reviewed_at', 'reviewed_by', 'updated_at'])
        announcement.agreements.filter(status=OwnerAnnouncementAgreement.Status.ACTIVE).update(
            status=OwnerAnnouncementAgreement.Status.TERMINATED,
        )
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=request.user,
            event_type=OwnerAnnouncementEvent.Type.WITHDRAWN,
            from_status=before,
            to_status=announcement.status,
        )
        notify_brokers(
            announcement,
            'announcement_withdrawn',
            f'The owner withdrew {announcement.property.title}.',
            f'withdrawn:{timezone.now().isoformat()}',
        )
        return Response(OwnerAnnouncementSerializer(announcement, context={'request': request}).data)


class BrokerAnnouncementListView(generics.ListAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = BROKER_REVIEW_PERMISSION
    serializer_class = BrokerAnnouncementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'property__listing_type', 'property__property_type']
    search_fields = [
        'property__title',
        'property__location',
        'owner_contact_name',
        'owner_contact_phone',
        'submitter__username',
        'submitter__email',
    ]
    ordering_fields = ['submitted_at', 'updated_at']
    ordering = ['-submitted_at']

    def get_queryset(self):
        return (
            OwnerAnnouncement.objects.select_related(
                'property',
                'property__administrative_location',
                'submitter',
                'reviewed_by',
            )
            .prefetch_related('property__images', 'agreements', 'events')
            .order_by(*self.ordering)
        )


class BrokerAnnouncementDecisionView(APIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = BROKER_REVIEW_PERMISSION

    @transaction.atomic
    def post(self, request, pk):
        announcement = get_object_or_404(
            OwnerAnnouncement.objects.select_for_update().select_related('property', 'submitter'),
            pk=pk,
        )
        serializer = BrokerAnnouncementDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data
        previous_status = announcement.status
        actor = request.user
        event_type_by_action = {
            'request_corrections': OwnerAnnouncementEvent.Type.CORRECTIONS_REQUESTED,
            'reject': OwnerAnnouncementEvent.Type.REJECTED,
            'suspend': OwnerAnnouncementEvent.Type.SUSPENDED,
            'approve': OwnerAnnouncementEvent.Type.APPROVED,
        }
        target_by_action = {
            'request_corrections': OwnerAnnouncement.Status.CORRECTIONS_REQUESTED,
            'reject': OwnerAnnouncement.Status.REJECTED,
            'suspend': OwnerAnnouncement.Status.SUSPENDED,
            'approve': OwnerAnnouncement.Status.APPROVED,
        }
        action = decision['action']
        if action == 'approve':
            is_renewal = (
                announcement.status in (OwnerAnnouncement.Status.APPROVED, OwnerAnnouncement.Status.EXPIRED)
                and announcement.renewal_requested_at is not None
            )
            if announcement.status not in (
                OwnerAnnouncement.Status.PENDING_REVIEW,
                OwnerAnnouncement.Status.CORRECTIONS_REQUESTED,
            ) and not is_renewal:
                raise ValidationError({'status': 'Only pending or corrected announcements can be approved.'})
            if is_renewal and decision['agreement_start_date'] > timezone.localdate():
                raise ValidationError({
                    'agreement_start_date': 'A renewal must start today or earlier to avoid a gap in public availability.',
                })
            if announcement.property.status not in (Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE):
                raise ValidationError({'property': 'Only available properties can be approved.'})
            end_date = decision['agreement_end_date']
            if end_date < decision['agreement_start_date'] or end_date < timezone.localdate():
                raise ValidationError({'agreement_end_date': 'The agreement must include a valid effective period.'})
            if decision['public_contact_visible'] and not (
                decision.get('public_contact_phone') or decision.get('public_contact_email')
            ):
                raise ValidationError({'public_contact_visible': 'Provide a public telephone number or email before showing owner contact details.'})
            agreement_start = decision['agreement_start_date']
            announcement.agreements.filter(status=OwnerAnnouncementAgreement.Status.ACTIVE).update(
                status=OwnerAnnouncementAgreement.Status.SUPERSEDED,
            )
            agreement = OwnerAnnouncementAgreement.objects.create(
                announcement=announcement,
                start_date=agreement_start,
                end_date=end_date,
                duration_months=decision['duration_months'],
                terms=decision['agreement_terms'],
                renewal_conditions=decision.get('renewal_conditions', ''),
                public_contact_visible=decision['public_contact_visible'],
                status=OwnerAnnouncementAgreement.Status.ACTIVE,
                approved_by=actor,
            )
            announcement.public_contact_name = decision.get('public_contact_name', '').strip()
            announcement.public_contact_phone = decision.get('public_contact_phone', '').strip()
            announcement.public_contact_email = decision.get('public_contact_email', '').strip()
            announcement.public_contact_visible = decision['public_contact_visible']
            announcement.property.exact_location_is_public = decision['exact_location_is_public']
            announcement.property.publication_status = Property.PublicationStatus.PUBLISHED
            announcement.property.save(update_fields=['exact_location_is_public', 'publication_status', 'updated_at'])
            event_details = {
                'agreement_id': agreement.pk,
                'agreement_start_date': agreement.start_date.isoformat(),
                'agreement_end_date': agreement.end_date.isoformat(),
                'duration_months': agreement.duration_months,
                'public_contact_visible': agreement.public_contact_visible,
                'exact_location_is_public': announcement.property.exact_location_is_public,
            }
        else:
            if action == 'suspend' and announcement.status != OwnerAnnouncement.Status.APPROVED:
                raise ValidationError({'status': 'Only approved announcements can be suspended.'})
            if action != 'suspend' and announcement.status not in (
                OwnerAnnouncement.Status.PENDING_REVIEW,
                OwnerAnnouncement.Status.CORRECTIONS_REQUESTED,
            ):
                raise ValidationError({'status': 'This announcement is not awaiting review.'})
            announcement.property.publication_status = (
                Property.PublicationStatus.PENDING_REVIEW
                if action == 'request_corrections'
                else Property.PublicationStatus.REJECTED
                if action == 'reject'
                else Property.PublicationStatus.SUSPENDED
            )
            announcement.property.save(update_fields=['publication_status', 'updated_at'])
            if action in ('reject', 'suspend'):
                announcement.agreements.filter(status=OwnerAnnouncementAgreement.Status.ACTIVE).update(
                    status=OwnerAnnouncementAgreement.Status.TERMINATED,
                )
            event_details = {}

        announcement.status = target_by_action[action]
        announcement.broker_feedback = decision.get('feedback', '').strip()
        announcement.reviewed_at = timezone.now()
        announcement.reviewed_by = actor
        announcement.renewal_requested_at = None
        announcement.save()
        OwnerAnnouncementEvent.objects.create(
            announcement=announcement,
            actor=actor,
            event_type=event_type_by_action[action],
            from_status=previous_status,
            to_status=announcement.status,
            details=event_details,
        )
        record_admin_action(
            actor,
            action=f'owner_announcement_{action}',
            object_type='owner_announcement',
            object_id=announcement.pk,
            changes={
                'from_status': previous_status,
                'to_status': announcement.status,
                'feedback_provided': bool(announcement.broker_feedback),
                **event_details,
            },
        )
        notify_user(
            announcement.submitter,
            announcement,
            f'announcement_{action}',
            {
                'approve': f'Your property announcement was approved: {announcement.property.title}.',
                'request_corrections': f'The broker requested corrections for {announcement.property.title}.',
                'reject': f'Your property announcement was rejected: {announcement.property.title}.',
                'suspend': f'Your property announcement was suspended: {announcement.property.title}.',
            }[action],
            f'announcement:{announcement.pk}:decision:{announcement.reviewed_at.isoformat()}:owner',
        )
        return Response(BrokerAnnouncementSerializer(
            announcement,
            context={'request': request},
        ).data)


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


class BrokerAgreementOverviewView(generics.ListAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = BROKER_REVIEW_PERMISSION
    serializer_class = BrokerAnnouncementSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['property__title', 'owner_contact_name', 'owner_contact_phone']

    def get_queryset(self):
        today = timezone.localdate()
        window_end = today + timedelta(days=30)
        return (
            OwnerAnnouncement.objects.filter(
                status=OwnerAnnouncement.Status.APPROVED,
            )
            .filter(
                Q(agreements__status=OwnerAnnouncementAgreement.Status.ACTIVE)
                & (
                    Q(agreements__end_date__lte=window_end)
                    | Q(agreements__end_date__lt=today)
                )
            )
            .select_related('property', 'submitter')
            .prefetch_related('property__images', 'agreements', 'events')
            .distinct()
            .order_by('agreements__end_date')
        )
