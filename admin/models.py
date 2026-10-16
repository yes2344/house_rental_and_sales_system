from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models


class BrokerageSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    platform_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='brokerage_settings',
        null=True,
        blank=True,
    )
    business_name = models.CharField(max_length=160, blank=True)
    site_name = models.CharField(max_length=100, default='Habasha Property Center')
    footer_copyright = models.CharField(max_length=200, blank=True)
    site_logo = models.ImageField(upload_to='site-branding/', blank=True)
    homepage_hero_image = models.ImageField(upload_to='site-branding/homepage/', blank=True)
    phone = models.CharField(max_length=50, blank=True)
    whatsapp_url = models.URLField(max_length=300, blank=True)
    telegram_url = models.URLField(max_length=300, blank=True)
    email = models.EmailField(blank=True)
    facebook_url = models.URLField(max_length=300, blank=True)
    instagram_url = models.URLField(max_length=300, blank=True)
    tiktok_url = models.URLField(max_length=300, blank=True)
    youtube_url = models.URLField(max_length=300, blank=True)
    linkedin_url = models.URLField(max_length=300, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Habasha Property Center contact settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        has_active_superuser_owner = self.platform_owner_id and get_user_model().objects.filter(
            pk=self.platform_owner_id,
            is_superuser=True,
            is_active=True,
        ).exists()
        if not has_active_superuser_owner:
            self.platform_owner = get_user_model().objects.filter(
                is_superuser=True,
                is_active=True,
            ).order_by('pk').first()
            if self.platform_owner is None:
                raise ValidationError(
                    'Create an active platform-owner account before saving Habasha Property Center contact settings.'
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.business_name or 'Habasha Property Center contact settings'


class SocialMediaLink(models.Model):
    class Platform(models.TextChoices):
        FACEBOOK = 'facebook', 'Facebook'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        TELEGRAM = 'telegram', 'Telegram'
        INSTAGRAM = 'instagram', 'Instagram'
        TIKTOK = 'tiktok', 'TikTok'
        YOUTUBE = 'youtube', 'YouTube'
        LINKEDIN = 'linkedin', 'LinkedIn'
        X = 'x', 'X'

    brokerage = models.ForeignKey(
        BrokerageSettings,
        on_delete=models.CASCADE,
        related_name='social_links',
    )
    platform = models.CharField(max_length=16, choices=Platform.choices)
    url = models.URLField(max_length=300)
    is_enabled = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'platform']
        constraints = [
            models.UniqueConstraint(
                fields=['brokerage', 'platform'],
                name='brokerage_unique_social_platform',
            ),
        ]

    def __str__(self):
        return self.get_platform_display()


class HomepageNote(models.Model):
    title = models.CharField(max_length=160, blank=True)
    text = models.TextField(max_length=2000)
    is_published = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return self.title or self.text[:60]


class PublicInformationPage(models.Model):
    class Page(models.TextChoices):
        ABOUT = 'about', 'About'
        CONTACT = 'contact', 'Contact'
        PROPERTY_MANAGEMENT = 'property-management', 'Property management'

    page = models.CharField(max_length=32, choices=Page.choices, unique=True)
    title_en = models.CharField(max_length=160)
    title_am = models.CharField(max_length=160)
    introduction_en = models.CharField(max_length=500)
    introduction_am = models.CharField(max_length=500)
    body_en = models.TextField(max_length=5000, blank=True)
    body_am = models.TextField(max_length=5000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page']

    def __str__(self):
        return self.get_page_display()


class AdminAuditEvent(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='admin_audit_events',
        null=True,
        blank=True,
    )
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=50)
    object_type = models.CharField(max_length=50)
    object_id = models.CharField(max_length=64)
    changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['object_type', 'object_id'], name='admin_audit_object_idx'),
            models.Index(fields=['-created_at'], name='admin_audit_created_idx'),
        ]

    def __str__(self):
        return f'{self.action}: {self.object_type} {self.object_id}'
