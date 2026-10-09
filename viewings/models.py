from django.conf import settings
from django.db import models

from properties.models import Property


class ViewingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROPOSED = 'proposed', 'Proposed'
        CONFIRMED = 'confirmed', 'Confirmed'
        REJECTED = 'rejected', 'Rejected'
        DECLINED = 'declined', 'Declined'

    STATUS_CHOICES = Status.choices

    property = models.ForeignKey(Property, related_name='viewing_requests', on_delete=models.CASCADE)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='viewing_requests',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    preferred_date = models.DateField()
    preferred_time = models.TimeField(null=True, blank=True)
    proposed_date = models.DateField(null=True, blank=True)
    proposed_time = models.TimeField(null=True, blank=True)
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    receipt_token_digest = models.CharField(max_length=64, null=True, blank=True, unique=True)
    guest_responded_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)
    agent_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_viewingrequest'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.property.title}'


class ViewingRequestEvent(models.Model):
    class Type(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        PROPOSAL_SENT = 'proposal_sent', 'Appointment proposed'
        PROPOSAL_REVISED = 'proposal_revised', 'Appointment proposal revised'
        PROPOSAL_ACCEPTED = 'proposal_accepted', 'Appointment proposal accepted'
        PROPOSAL_DECLINED = 'proposal_declined', 'Appointment proposal declined'
        REJECTED = 'rejected', 'Request declined by property manager'

    viewing_request = models.ForeignKey(
        ViewingRequest,
        related_name='events',
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='viewing_request_events',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=32, choices=Type.choices)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    proposed_date = models.DateField(null=True, blank=True)
    proposed_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']

    def __str__(self):
        return f'{self.viewing_request_id}: {self.event_type}'
