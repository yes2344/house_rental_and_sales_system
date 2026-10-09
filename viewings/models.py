from django.conf import settings
from django.db import models

from properties.models import Property


class ViewingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        REJECTED = 'rejected', 'Rejected'

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
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    message = models.TextField(blank=True)
    agent_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_viewingrequest'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.property.title}'
