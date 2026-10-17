from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from properties.models import Property


class OwnerAnnouncement(models.Model):
    class Status(models.TextChoices):
        PENDING_REVIEW = 'pending_review', 'Pending review'
        CORRECTIONS_REQUESTED = 'corrections_requested', 'Corrections requested'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SUSPENDED = 'suspended', 'Suspended'
        EXPIRED = 'expired', 'Expired'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name='owner_announcement',
    )
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owner_announcements',
    )
    owner_contact_name = models.CharField(max_length=200)
    owner_contact_phone = models.CharField(max_length=50)
    owner_contact_email = models.EmailField(blank=True)
    public_contact_name = models.CharField(max_length=200, blank=True)
    public_contact_phone = models.CharField(max_length=50, blank=True)
    public_contact_email = models.EmailField(blank=True)
    public_contact_visible = models.BooleanField(default=False)
    authorization_confirmed = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField()
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING_REVIEW,
    )
    broker_feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewed_owner_announcements',
        null=True,
        blank=True,
    )
    assigned_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_owner_announcements',
        null=True,
        blank=True,
    )
    renewal_requested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='owner_announce_status_idx'),
            models.Index(fields=['submitter', '-submitted_at'], name='owner_announce_owner_idx'),
            models.Index(fields=['assigned_reviewer', 'status'], name='owner_announce_reviewer_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(authorization_confirmed=True),
                name='owner_announcement_authorized',
            ),
        ]

    def __str__(self):
        return f'{self.property.title} ({self.get_status_display()})'


class OwnerAnnouncementAgreement(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUPERSEDED = 'superseded', 'Superseded'
        EXPIRED = 'expired', 'Expired'
        TERMINATED = 'terminated', 'Terminated'

    announcement = models.ForeignKey(
        OwnerAnnouncement,
        on_delete=models.CASCADE,
        related_name='agreements',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    duration_months = models.PositiveSmallIntegerField()
    terms = models.TextField(max_length=4000)
    renewal_conditions = models.TextField(max_length=2000, blank=True)
    public_contact_visible = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='approved_owner_announcement_agreements',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['status', 'end_date'], name='owner_agreement_expiry_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F('start_date')),
                name='owner_agreement_valid_dates',
            ),
            models.CheckConstraint(
                condition=Q(duration_months__gte=1, duration_months__lte=120),
                name='owner_agreement_duration_range',
            ),
            models.UniqueConstraint(
                fields=['announcement'],
                condition=Q(status='active'),
                name='owner_announcement_one_active_agreement',
            ),
        ]

    def clean(self):
        super().clean()
        if self.end_date < self.start_date:
            raise ValidationError({'end_date': 'Agreement expiry must be on or after its start date.'})

    def __str__(self):
        return f'{self.announcement.property.title}: {self.start_date}–{self.end_date}'


class OwnerAnnouncementEvent(models.Model):
    class Type(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        ASSIGNED = 'assigned', 'Assigned for review'
        UNASSIGNED = 'unassigned', 'Review assignment removed'
        CORRECTIONS_REQUESTED = 'corrections_requested', 'Corrections requested'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        EDITED = 'edited', 'Owner edited'
        RENEWAL_REQUESTED = 'renewal_requested', 'Renewal requested'
        SUSPENDED = 'suspended', 'Suspended'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        EXPIRED = 'expired', 'Expired'

    announcement = models.ForeignKey(
        OwnerAnnouncement,
        on_delete=models.CASCADE,
        related_name='events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='owner_announcement_events',
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=32, choices=Type.choices)
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['announcement', '-created_at'], name='owner_announce_event_idx'),
        ]


class InAppNotification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='marketplace_notifications',
    )
    announcement = models.ForeignKey(
        OwnerAnnouncement,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
    )
    notification_type = models.CharField(max_length=40)
    message = models.CharField(max_length=500)
    idempotency_key = models.CharField(max_length=180, unique=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read_at', '-created_at'], name='notify_recipient_read_idx'),
        ]

    def __str__(self):
        return f'{self.notification_type} for {self.recipient}'
