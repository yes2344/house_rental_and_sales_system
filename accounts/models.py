import hashlib
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

class Profile(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        OWNER = 'owner', 'Property owner'
        BROKER = 'broker', 'Authorized broker'
        ADMINISTRATOR = 'administrator', 'Delegated administrator'

    class Permission(models.TextChoices):
        PROPERTY_VIEW_ALL = 'properties.view_all', 'View all listings'
        PROPERTY_MODERATE = 'properties.moderate', 'Moderate listings'
        PROPERTY_EDIT_ALL = 'properties.edit_all', 'Edit all listings'
        PROPERTY_DELETE_ALL = 'properties.delete_all', 'Delete listings'
        PROPERTY_MANAGE_ASSIGNED = 'properties.manage_assigned', 'Manage assigned listings'
        VIEWING_VIEW_ALL = 'viewings.view_all', 'View all viewing requests'
        VIEWING_MANAGE_ALL = 'viewings.manage_all', 'Manage all viewing requests'
        VIEWING_MANAGE_ASSIGNED = 'viewings.manage_assigned', 'Manage assigned viewing requests'
        USERS_MANAGE = 'users.manage', 'Manage ordinary user accounts'
        OWNER_ANNOUNCEMENTS_REVIEW = 'announcements.review', 'Review owner property announcements'
        REPORTS_REVIEW = 'reports.review', 'Review listing reports'
        STATISTICS_VIEW = 'statistics.view', 'View management statistics'
        AUDIT_VIEW = 'audit.view', 'View audit records'
        BROKERS_ASSIGN = 'brokers.assign', 'Assign brokers to listings'
        SETTINGS_MANAGE = 'settings.manage', 'Manage platform settings'
        STAFF_MANAGE = 'staff.manage', 'Manage delegated accounts'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=50, blank=True)
    broker_approved = models.BooleanField(default=False)
    management_permissions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=['customer', 'owner', 'broker', 'administrator']),
                name='account_profile_valid_role',
            ),
            models.CheckConstraint(condition=Q(role='broker') | Q(broker_approved=False), name='account_approval_requires_broker'),
        ]

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'


class UserPreferences(models.Model):
    class Theme(models.TextChoices):
        LIGHT = 'light', 'Light'
        DARK = 'dark', 'Dark'
        SYSTEM = 'system', 'System default'

    class Locale(models.TextChoices):
        ENGLISH = 'en', 'English'
        AMHARIC = 'am', 'Amharic'

    class Density(models.TextChoices):
        COMFORTABLE = 'comfortable', 'Comfortable'
        COMPACT = 'compact', 'Compact'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences',
    )
    theme = models.CharField(max_length=10, choices=Theme.choices, default=Theme.SYSTEM)
    locale = models.CharField(max_length=2, choices=Locale.choices, default=Locale.ENGLISH)
    density = models.CharField(max_length=12, choices=Density.choices, default=Density.COMFORTABLE)
    reduced_motion = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Preferences for {self.user}'


class TabSessionToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tab_session_tokens',
    )
    token_digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'expires_at'], name='account_tab_token_user_exp_idx'),
        ]

    @classmethod
    def issue(cls, user):
        import secrets

        token = secrets.token_urlsafe(32)
        token_digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
        session_token = cls.objects.create(
            user=user,
            token_digest=token_digest,
            expires_at=timezone.now() + settings.API_TAB_SESSION_LIFETIME,
        )
        return session_token, token

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])


class DelegatedAccountInvitation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegated_invitations',
    )
    token_digest = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_delegated_invitations',
        null=True,
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'expires_at'], name='account_invite_user_exp_idx')]

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @classmethod
    def issue(cls, user, actor, *, lifetime=timedelta(days=2)):
        import secrets

        token = secrets.token_urlsafe(32)
        invitation = cls.objects.create(
            user=user,
            created_by=actor,
            token_digest=cls.digest(token),
            expires_at=timezone.now() + lifetime,
        )
        return invitation, token

    def is_valid(self):
        return self.accepted_at is None and self.expires_at > timezone.now() and not self.user.is_active
