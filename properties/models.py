from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models, transaction
from django.db.models import Q
from django.utils.text import slugify


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    name_am = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Property(models.Model):
    class ListingType(models.TextChoices):
        SALE = 'sale', 'For Sale'
        RENT = 'rent', 'For Rent'

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RENTED = 'rented', 'Rented'
        SOLD = 'sold', 'Sold'
        INACTIVE = 'inactive', 'Inactive'
        LEGACY_ACTIVE = 'active', 'Active (legacy)'

    class PublicationStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_REVIEW = 'pending_review', 'Pending review'
        PUBLISHED = 'published', 'Published'
        REJECTED = 'rejected', 'Rejected'
        SUSPENDED = 'suspended', 'Suspended'

    class AreaUnit(models.TextChoices):
        SQUARE_METRES = 'sqm', 'Square metres'
        SQUARE_FEET = 'sqft', 'Square feet'

    class RentalFrequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    STATUS_CHOICES = [
        (Status.LEGACY_ACTIVE, 'Active'),
        (Status.AVAILABLE, 'Available'),
        (Status.RENTED, 'Rented'),
        (Status.SOLD, 'Sold'),
        (Status.INACTIVE, 'Inactive'),
    ]
    LISTING_TYPE_CHOICES = ListingType.choices
    PROPERTY_TYPES = [
        ('house', 'House'),
        ('villa', 'Villa'),
        ('apartment', 'Apartment'),
        ('land', 'Land'),
        ('commercial', 'Commercial'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    location = models.CharField(max_length=200, db_index=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('-90')), MaxValueValidator(Decimal('90'))],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('-180')), MaxValueValidator(Decimal('180'))],
    )
    exact_location_is_public = models.BooleanField(default=False)
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPES, default='house')
    listing_type = models.CharField(max_length=20, choices=LISTING_TYPE_CHOICES, default=ListingType.SALE)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    rental_frequency = models.CharField(
        max_length=10,
        choices=RentalFrequency.choices,
        blank=True,
        default='',
    )
    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.PositiveIntegerField(default=0)
    area_sqft = models.PositiveIntegerField(default=0)
    area_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    area_unit = models.CharField(
        max_length=5,
        choices=AreaUnit.choices,
        blank=True,
        default='',
    )
    description = models.TextField()
    features = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=Status.AVAILABLE)
    publication_status = models.CharField(
        max_length=20,
        choices=PublicationStatus.choices,
        default=PublicationStatus.PENDING_REVIEW,
    )
    is_featured = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='owned_properties',
        null=True,
        blank=True,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='submitted_properties',
        null=True,
        blank=True,
    )
    advertising_authorized = models.BooleanField(default=False)
    contact_publicly_visible = models.BooleanField(default=False)
    moderation_note = models.TextField(blank=True)
    assigned_brokers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='PropertyBrokerAssignment',
        related_name='assigned_properties',
        through_fields=('property', 'broker'),
        blank=True,
    )
    amenities = models.ManyToManyField(Amenity, related_name='properties', blank=True)
    contact_name = models.CharField(max_length=200, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'user_property'
        indexes = [
            models.Index(
                fields=['publication_status', 'status', 'listing_type', '-created_at'],
                name='property_public_search_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(price__gt=0), name='property_price_positive'),
            models.CheckConstraint(
                condition=Q(
                    property_type__in=['house', 'villa', 'apartment', 'land', 'commercial']
                ),
                name='property_valid_category',
            ),
            models.CheckConstraint(
                condition=Q(status__in=['active', 'available', 'rented', 'sold', 'inactive']),
                name='property_valid_status',
            ),
            models.CheckConstraint(
                condition=(
                    Q(status__in=['active', 'available', 'inactive'])
                    | Q(status='rented', listing_type='rent')
                    | Q(status='sold', listing_type='sale')
                ),
                name='property_status_listing_type_compatible',
            ),
            models.CheckConstraint(
                condition=Q(publication_status__in=[
                    'draft', 'pending_review', 'published', 'rejected', 'suspended',
                ]),
                name='property_valid_publication_status',
            ),
            models.CheckConstraint(
                condition=Q(area_value__isnull=True) | Q(area_value__gt=0),
                name='property_area_positive',
            ),
            models.CheckConstraint(
                condition=(
                    Q(latitude__isnull=True, longitude__isnull=True)
                    | Q(latitude__isnull=False, longitude__isnull=False)
                ),
                name='property_coordinates_paired',
            ),
            models.CheckConstraint(
                condition=Q(latitude__isnull=True) | Q(latitude__gte=-90, latitude__lte=90),
                name='property_latitude_in_range',
            ),
            models.CheckConstraint(
                condition=Q(longitude__isnull=True) | Q(longitude__gte=-180, longitude__lte=180),
                name='property_longitude_in_range',
            ),
            models.CheckConstraint(
                condition=(
                    Q(area_value__isnull=True, area_unit='')
                    | Q(area_value__gt=0, area_unit__in=['sqm', 'sqft'])
                ),
                name='property_area_unit_matches_value',
            ),
            models.CheckConstraint(
                condition=Q(rental_frequency__in=['', 'daily', 'weekly', 'monthly', 'yearly']),
                name='property_valid_rental_frequency',
            ),
            models.CheckConstraint(
                condition=Q(listing_type='rent') | Q(rental_frequency=''),
                name='property_frequency_only_for_rent',
            ),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or 'property'
            self.slug = base_slug
            suffix = 2
            while type(self).objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base_slug}-{suffix}'
                suffix += 1
        super().save(*args, **kwargs)

    @property
    def formatted_price(self):
        return f'ETB {self.price:,.2f}'

    @property
    def has_public_coordinates(self):
        return (
            self.exact_location_is_public
            and self.latitude is not None
            and self.longitude is not None
        )


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to='property_images/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
    )
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_propertyimage'
        ordering = ['pk']
        constraints = [
            models.UniqueConstraint(
                fields=['property'],
                condition=Q(is_primary=True),
                name='property_image_one_primary_per_property',
            ),
        ]

    def save(self, *args, **kwargs):
        if self._state.adding and self.property_id:
            with transaction.atomic():
                Property.objects.select_for_update().get(pk=self.property_id)
                if PropertyImage.objects.filter(property_id=self.property_id).count() >= 10:
                    raise ValidationError({'image': 'A property can have at most 10 images.'})
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.property.title} image'


class PropertyBrokerAssignment(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='broker_assignments')
    broker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='property_broker_assignments',
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='granted_property_broker_assignments',
        null=True,
        blank=True,
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['property', 'broker'],
                name='property_broker_assignment_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['broker', 'granted_at'], name='broker_assignment_user_idx'),
        ]

    def __str__(self):
        return f'{self.broker} assigned to {self.property}'


class ListingReport(models.Model):
    class Reason(models.TextChoices):
        INACCURATE = 'inaccurate', 'Inaccurate information'
        UNAVAILABLE = 'unavailable', 'Property unavailable'
        FRAUD = 'fraud', 'Suspected fraud'
        INAPPROPRIATE = 'inappropriate', 'Inappropriate content'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        REVIEWED = 'reviewed', 'Reviewed'
        DISMISSED = 'dismissed', 'Dismissed'
        ACTION_TAKEN = 'action_taken', 'Action taken'

    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        related_name='reports',
        null=True,
        blank=True,
    )
    property_title = models.CharField(max_length=200)
    reporter_name = models.CharField(max_length=200)
    reporter_email = models.EmailField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    details = models.TextField(blank=True, max_length=2000)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    moderator_notes = models.TextField(blank=True, max_length=2000)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewed_listing_reports',
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='listing_report_status_idx'),
        ]

    def save(self, *args, **kwargs):
        if self.property_id and not self.property_title:
            self.property_title = self.property.title
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_reason_display()} report for {self.property_title}'
