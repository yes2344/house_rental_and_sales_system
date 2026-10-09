from django.conf import settings
from django.db import models
from django.db.models import Q

class Profile(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        OWNER = 'owner', 'Property owner'
        BROKER = 'broker', 'Authorized broker'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=50, blank=True)
    broker_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=['customer', 'owner', 'broker']),
                name='account_profile_valid_role',
            ),
            models.CheckConstraint(
                condition=Q(role='broker') | Q(broker_approved=False),
                name='account_approval_requires_broker',
            ),
        ]

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'
