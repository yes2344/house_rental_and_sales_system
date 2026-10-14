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


class Location(models.Model):
    class Type(models.TextChoices):
        COUNTRY = 'country', 'Country'
        REGION = 'region', 'Region'
        CITY_ADMINISTRATION = 'city_administration', 'City administration'
        CITY = 'city', 'City or town'
        SUBCITY = 'subcity', 'Sub-city / kifle ketema'
        WOREDA = 'woreda', 'Woreda'
        NEIGHBORHOOD = 'neighborhood', 'Neighborhood / local area'

    name = models.CharField(max_length=120)
    name_am = models.CharField(max_length=120, blank=True)
    aliases_en = models.JSONField(default=list, blank=True)
    aliases_am = models.JSONField(default=list, blank=True)
    slug = models.SlugField(max_length=140)
    location_type = models.CharField(max_length=24, choices=Type.choices)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='children',
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
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

    class Meta:
        ordering = ['display_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['parent', 'slug'],
                name='location_unique_sibling_slug',
            ),
            models.UniqueConstraint(
                fields=['slug'],
                condition=models.Q(parent__isnull=True),
                name='location_unique_root_slug',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(latitude__isnull=True, longitude__isnull=True)
                    | models.Q(latitude__isnull=False, longitude__isnull=False)
                ),
                name='location_coordinates_paired',
            ),
            models.CheckConstraint(
                condition=models.Q(latitude__isnull=True) | models.Q(latitude__gte=-90, latitude__lte=90),
                name='location_latitude_in_range',
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__isnull=True) | models.Q(longitude__gte=-180, longitude__lte=180),
                name='location_longitude_in_range',
            ),
        ]
        indexes = [
            models.Index(fields=['parent', 'is_active', 'display_order'], name='location_parent_active_idx'),
        ]

    def clean(self):
        super().clean()
        allowed_parent_types = {
            self.Type.COUNTRY: {None},
            self.Type.REGION: {self.Type.COUNTRY},
            self.Type.CITY_ADMINISTRATION: {self.Type.COUNTRY},
            self.Type.CITY: {self.Type.COUNTRY, self.Type.REGION, self.Type.CITY_ADMINISTRATION},
            self.Type.SUBCITY: {self.Type.CITY, self.Type.CITY_ADMINISTRATION},
            self.Type.WOREDA: {self.Type.CITY, self.Type.CITY_ADMINISTRATION, self.Type.SUBCITY},
            self.Type.NEIGHBORHOOD: {self.Type.CITY, self.Type.CITY_ADMINISTRATION, self.Type.SUBCITY, self.Type.WOREDA},
        }
        parent_type = self.parent.location_type if self.parent_id and self.parent else None
        allowed_types = allowed_parent_types.get(self.location_type)
        if allowed_types is None:
            raise ValidationError({'location_type': 'Choose a supported location type.'})
        if parent_type not in allowed_types:
            raise ValidationError({'parent': 'Choose a parent location compatible with this location type.'})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


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
        EXPIRED = 'expired', 'Expired'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    class ServiceType(models.TextChoices):
        BROKER_MANAGED = 'broker_managed', 'Broker-managed'
        OWNER_ANNOUNCED = 'owner_announced', 'Owner-announced'

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
        ('condominium', 'Condominium'),
        ('land', 'Land'),
        ('office', 'Office'),
        ('shop', 'Shop'),
        ('warehouse', 'Warehouse'),
        ('commercial', 'Commercial'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    location = models.CharField(max_length=200, db_index=True)
    administrative_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='properties',
        null=True,
        blank=True,
    )
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
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.BROKER_MANAGED,
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
            models.Index(
                fields=['administrative_location', 'publication_status', 'status'],
                name='property_location_public_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(price__gt=0), name='property_price_positive'),
            models.CheckConstraint(
                condition=Q(
                    property_type__in=[
                        'house', 'villa', 'apartment', 'condominium', 'land',
                        'office', 'shop', 'warehouse', 'commercial', 'other',
                    ]
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
                    'expired', 'withdrawn',
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
        price = f'ETB {self.price:,.2f}'
        if self.listing_type == self.ListingType.RENT and self.rental_frequency:
            period = {
                self.RentalFrequency.DAILY: 'per day',
                self.RentalFrequency.WEEKLY: 'per week',
                self.RentalFrequency.MONTHLY: 'per month',
                self.RentalFrequency.YEARLY: 'per year',
            }[self.rental_frequency]
            return f'{price} / {period}'
        return price

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
