from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from PIL import Image, ImageChops

from accounts.models import Profile
from admin.models import AdminAuditEvent
from properties.image_processing import watermark_image
from properties.models import Amenity, Location, Property, PropertyBrokerAssignment, PropertyImage
from properties.serializers import LocationSerializer


class PropertyConstraintTests(TestCase):
    def make_property(self, **overrides):
        values = {
            'title': 'Constraint Test Property',
            'location': 'Submitted location',
            'property_type': 'house',
            'listing_type': Property.ListingType.SALE,
            'price': 100000,
            'description': 'A test listing.',
            'status': Property.Status.AVAILABLE,
        }
        values.update(overrides)
        return Property.objects.create(**values)

    def test_zero_price_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(price=0)

    def test_negative_price_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(price=-1)

    def test_sold_status_requires_sale_listing(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(
                    listing_type=Property.ListingType.RENT,
                    status=Property.Status.SOLD,
                )

    def test_rented_sale_listing_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(
                    listing_type=Property.ListingType.SALE,
                    status=Property.Status.RENTED,
                )

    def test_existing_active_status_remains_valid_for_legacy_data(self):
        property_obj = self.make_property(status=Property.Status.LEGACY_ACTIVE)
        self.assertEqual(property_obj.status, 'active')

    def test_property_can_store_area_with_a_supported_measurement_unit(self):
        property_obj = self.make_property(area_value='120.50', area_unit=Property.AreaUnit.SQUARE_METRES)
        property_obj.refresh_from_db()

        self.assertEqual(property_obj.area_value, Decimal('120.50'))
        self.assertEqual(property_obj.area_unit, Property.AreaUnit.SQUARE_METRES)

    def test_zero_area_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(area_value=0, area_unit=Property.AreaUnit.SQUARE_FEET)

    def test_area_value_requires_a_supported_unit(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(area_value=120, area_unit='acres')

    def test_rental_frequency_is_rejected_for_sale_listings(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(
                    listing_type=Property.ListingType.SALE,
                    rental_frequency=Property.RentalFrequency.MONTHLY,
                )

    def test_rental_frequency_can_be_stored_for_rental_listings(self):
        property_obj = self.make_property(
            listing_type=Property.ListingType.RENT,
            rental_frequency=Property.RentalFrequency.MONTHLY,
        )

        self.assertEqual(property_obj.rental_frequency, Property.RentalFrequency.MONTHLY)

    def test_suspended_publication_status_is_valid(self):
        property_obj = self.make_property(publication_status=Property.PublicationStatus.SUSPENDED)

        self.assertEqual(property_obj.publication_status, Property.PublicationStatus.SUSPENDED)

    def test_coordinates_are_optional_but_must_be_paired(self):
        property_obj = self.make_property()
        self.assertIsNone(property_obj.latitude)
        self.assertIsNone(property_obj.longitude)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(latitude=Decimal('10.300000'))

    def test_database_rejects_coordinates_outside_geographic_ranges(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(
                    latitude=Decimal('91.000000'),
                    longitude=Decimal('37.000000'),
                )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(
                    latitude=Decimal('10.000000'),
                    longitude=Decimal('181.000000'),
                )


class PublicPropertyApiTests(APITestCase):
    def setUp(self):
        self.property = Property.objects.create(
            title='Available family house',
            slug='available-family-house-api',
            location='Submitted location',
            property_type='house',
            listing_type=Property.ListingType.SALE,
            price=500000,
            bedrooms=3,
            bathrooms=2,
            area_sqft=1500,
            description='A family home with a garden.',
            features='Garden',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        self.garden, _ = Amenity.objects.get_or_create(
            name='Garden',
            defaults={'slug': 'garden'},
        )
        self.property.amenities.add(self.garden)

    def create_public_property(
        self,
        slug,
        *,
        listing_type=Property.ListingType.SALE,
        property_type='house',
        price=100000,
        rental_frequency='',
        location=None,
    ):
        return Property.objects.create(
            title=slug.replace('-', ' ').title(),
            slug=slug,
            location='Submitted location',
            administrative_location=location,
            property_type=property_type,
            listing_type=listing_type,
            price=price,
            rental_frequency=rental_frequency,
            description='Published test listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

    def test_public_list_returns_paginated_etb_properties(self):
        response = self.client.get(reverse('api:property-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        result = response.data['results'][0]
        self.assertEqual(result['currency'], 'ETB')
        self.assertEqual(result['category'], 'house')
        self.assertEqual(result['status'], 'available')
        self.assertNotIn('contact_phone', result)
        self.assertNotIn('owner', result)
        self.assertIn('rental_frequency', result)
        self.assertIn('created_at', result)
        self.assertEqual(result['slug'], self.property.slug)

    def test_public_property_type_options_match_the_model_choices(self):
        response = self.client.get(reverse('api:property-type-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            [
                {'value': value, 'label': label}
                for value, label in Property.PROPERTY_TYPES
            ],
        )

    def test_transaction_type_filter_excludes_the_other_listing_type(self):
        rental = self.create_public_property(
            'available-rental-property',
            listing_type=Property.ListingType.RENT,
            rental_frequency=Property.RentalFrequency.MONTHLY,
            price=25000,
        )

        for listing_type, expected_slug in (
            (Property.ListingType.RENT, rental.slug),
            (Property.ListingType.SALE, self.property.slug),
        ):
            with self.subTest(listing_type=listing_type):
                response = self.client.get(
                    reverse('api:property-list'),
                    {'listing_type': listing_type},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'][0]['slug'], expected_slug)

    def test_price_sorting_uses_numeric_prices_with_stable_sale_and_rental_period_groups(self):
        sale_high = self.create_public_property('sale-high-price', price=1000000)
        sale_equal = self.create_public_property('sale-equal-price', price=500000)
        daily = self.create_public_property(
            'daily-rental',
            listing_type=Property.ListingType.RENT,
            rental_frequency=Property.RentalFrequency.DAILY,
            price=900,
        )
        weekly = self.create_public_property(
            'weekly-rental',
            listing_type=Property.ListingType.RENT,
            rental_frequency=Property.RentalFrequency.WEEKLY,
            price=1200,
        )
        monthly = self.create_public_property(
            'monthly-rental',
            listing_type=Property.ListingType.RENT,
            rental_frequency=Property.RentalFrequency.MONTHLY,
            price=300,
        )
        yearly = self.create_public_property(
            'yearly-rental',
            listing_type=Property.ListingType.RENT,
            rental_frequency=Property.RentalFrequency.YEARLY,
            price=100,
        )

        ascending = self.client.get(reverse('api:property-list'), {'ordering': 'price'})
        descending = self.client.get(reverse('api:property-list'), {'ordering': '-price'})

        self.assertEqual(ascending.status_code, 200)
        self.assertEqual(
            [item['slug'] for item in ascending.data['results']],
            [
                self.property.slug,
                sale_equal.slug,
                sale_high.slug,
                daily.slug,
                weekly.slug,
                monthly.slug,
                yearly.slug,
            ],
        )
        self.assertEqual(
            [item['slug'] for item in descending.data['results']],
            [
                sale_high.slug,
                self.property.slug,
                sale_equal.slug,
                daily.slug,
                weekly.slug,
                monthly.slug,
                yearly.slug,
            ],
        )

    def test_date_sort_options_are_stable_and_reject_other_ordering_fields(self):
        now = timezone.now()
        earlier = now - timedelta(days=2)
        middle = now - timedelta(days=1)
        later = now
        older_property = self.create_public_property('older-date-property')
        tie_property = self.create_public_property('tied-date-property')
        newer_property = self.create_public_property('newer-date-property')
        Property.objects.filter(pk=self.property.pk).update(created_at=middle)
        Property.objects.filter(pk=tie_property.pk).update(created_at=middle)
        Property.objects.filter(pk=older_property.pk).update(created_at=earlier)
        Property.objects.filter(pk=newer_property.pk).update(created_at=later)

        newest_first = self.client.get(
            reverse('api:property-list'),
            {'ordering': '-created_at'},
        )
        oldest_first = self.client.get(
            reverse('api:property-list'),
            {'ordering': 'created_at'},
        )
        invalid = self.client.get(
            reverse('api:property-list'),
            {'ordering': '-area_sqft'},
        )
        default_order = self.client.get(reverse('api:property-list'))

        self.assertEqual(newest_first.status_code, 200)
        self.assertEqual(
            [item['slug'] for item in newest_first.data['results'][:3]],
            [newer_property.slug, tie_property.slug, self.property.slug],
        )
        self.assertEqual(oldest_first.status_code, 200)
        self.assertEqual(
            [item['slug'] for item in oldest_first.data['results'][:3]],
            [older_property.slug, self.property.slug, tie_property.slug],
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('ordering', invalid.data['error']['details'])
        self.assertEqual(
            [item['slug'] for item in default_order.data['results'][:3]],
            [newer_property.slug, tie_property.slug, self.property.slug],
        )

    def test_invalid_and_incompatible_location_filters_are_rejected(self):
        country = Location.objects.create(
            name='Validation Test Country',
            slug='validation-test-country',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Validation Test City',
            slug='validation-test-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        other_city = Location.objects.create(
            name='Other Validation Test City',
            slug='other-validation-test-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        subcity = Location.objects.create(
            name='Validation Test Subcity',
            slug='validation-test-subcity',
            location_type=Location.Type.SUBCITY,
            parent=city,
        )

        invalid_location = self.client.get(
            reverse('api:property-list'),
            {'location_id': 999999},
        )
        invalid_city_type = self.client.get(
            reverse('api:property-list'),
            {'city_id': country.id},
        )
        incompatible_pair = self.client.get(
            reverse('api:property-list'),
            {'city_id': other_city.id, 'location_id': subcity.id},
        )

        self.assertEqual(invalid_location.status_code, 400)
        self.assertEqual(invalid_city_type.status_code, 400)
        self.assertEqual(incompatible_pair.status_code, 400)

    def test_unsupported_property_type_and_duplicate_search_or_sort_values_are_rejected(self):
        invalid_type = self.client.get(
            reverse('api:property-list'),
            {'property_type': 'unsupported-type'},
        )
        duplicate_search = self.client.get(
            f"{reverse('api:property-list')}?search=house&search=rent",
        )
        duplicate_ordering = self.client.get(
            f"{reverse('api:property-list')}?ordering=price&ordering=-price",
        )

        self.assertEqual(invalid_type.status_code, 400)
        self.assertEqual(duplicate_search.status_code, 400)
        self.assertEqual(duplicate_ordering.status_code, 400)

    def test_city_filter_uses_location_hierarchy_and_returns_location_path(self):
        country = Location.objects.create(
            name='Test Country City Filter',
            slug='test-country-city-filter',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Test City Filter',
            name_am='የሙከራ ከተማ',
            slug='test-city-filter',
            location_type=Location.Type.CITY,
            parent=country,
        )
        subcity = Location.objects.create(
            name='Test Area Filter',
            name_am='የሙከራ አካባቢ',
            slug='test-area-filter',
            location_type=Location.Type.SUBCITY,
            parent=city,
        )
        other_city = Location.objects.create(
            name='Other Test City Filter',
            slug='other-test-city-filter',
            location_type=Location.Type.CITY,
            parent=country,
        )
        self.create_public_property(
            'same-city-apartment-filter-decoy',
            property_type='apartment',
            price=500000,
            location=subcity,
        )
        self.create_public_property(
            'other-city-house-filter-decoy',
            property_type='house',
            price=500000,
            location=other_city,
        )
        self.property.administrative_location = subcity
        self.property.save(update_fields=['administrative_location'])

        filtered = self.client.get(
            reverse('api:property-list'),
            {
                'city_id': city.id,
                'property_type': 'house',
                'min_price': '400000',
                'max_price': '600000',
            },
        )
        cities = self.client.get(reverse('api:location-list'), {'types': 'city,city_administration'})

        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.data['count'], 1)
        self.assertEqual(filtered.data['results'][0]['location_path'][-1]['id'], subcity.id)
        self.assertEqual(filtered.data['results'][0]['slug'], self.property.slug)
        self.assertCountEqual([item['id'] for item in cities.data], [city.id, other_city.id])

    def test_broker_managed_listing_exposes_the_approved_brokers_public_account_contacts(self):
        country = Location.objects.create(
            name='Public Broker Contact Country',
            slug='public-broker-contact-country',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Public Broker Contact City',
            slug='public-broker-contact-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        broker = get_user_model().objects.create_user(
            username='public-listing-broker',
            email='broker@example.com',
        )
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=city,
            phone='+251911222333',
        )
        self.property.submitted_by = broker
        self.property.contact_phone = '+251911222333'
        self.property.contact_email = 'broker@example.com'
        self.property.save(update_fields=['submitted_by', 'contact_phone', 'contact_email'])
        PropertyBrokerAssignment.objects.create(property=self.property, broker=broker)

        response = self.client.get(reverse('api:property-list'))
        result = response.data['results'][0]

        self.assertEqual(result['public_contact_phone'], '+251911222333')
        self.assertEqual(result['public_contact_email'], 'broker@example.com')

    def test_unapproved_broker_contact_is_not_public(self):
        broker = get_user_model().objects.create_user(
            username='unapproved-listing-broker',
            email='private-broker@example.com',
        )
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=False,
            phone='+251911222333',
        )
        self.property.submitted_by = broker
        self.property.contact_phone = '+251911222333'
        self.property.contact_email = 'private-broker@example.com'
        self.property.save(update_fields=['submitted_by', 'contact_phone', 'contact_email'])

        response = self.client.get(reverse('api:property-list'))

        self.assertEqual(response.data['results'][0]['public_contact_phone'], '')
        self.assertEqual(response.data['results'][0]['public_contact_email'], '')

    def test_formatted_rent_price_includes_period_and_sale_price_does_not(self):
        self.property.listing_type = Property.ListingType.RENT
        self.property.rental_frequency = Property.RentalFrequency.MONTHLY
        self.assertEqual(self.property.formatted_price, 'ETB 500,000.00 / per month')

        self.property.listing_type = Property.ListingType.SALE
        self.property.rental_frequency = ''
        self.assertEqual(self.property.formatted_price, 'ETB 500,000.00')

    def test_public_amenity_list_returns_existing_localized_options(self):
        response = self.client.get(reverse('api:amenity-list'))

        self.assertEqual(response.status_code, 200)
        garden = next(item for item in response.data['results'] if item['slug'] == 'garden')
        self.assertEqual(garden, {
            'id': self.garden.id,
            'name': 'Garden',
            'name_am': '',
            'slug': 'garden',
        })

    def test_combined_filters_and_amenities_are_applied(self):
        response = self.client.get(
            reverse('api:property-list'),
            {
                'listing_type': 'sale',
                'property_type': 'house',
                'min_price': '400000',
                'max_price': '600000',
                'min_bedrooms': '3',
                'min_size': '1000',
                'amenities': 'garden',
                'search': 'family',
                'ordering': 'price',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], self.property.slug)

    def test_english_and_amharic_bathroom_search_use_structured_count(self):
        Property.objects.create(
            title='No bathroom count',
            slug='no-bathroom-count-search',
            location='Submitted location',
            property_type='house',
            listing_type=Property.ListingType.SALE,
            price=250000,
            bathrooms=0,
            description='Does not match the structured bathroom filter.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

        for term in ('bathroom', 'መታጠቢያ'):
            with self.subTest(term=term):
                response = self.client.get(reverse('api:property-list'), {'search': term})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'][0]['slug'], self.property.slug)

    def test_mixed_language_search_applies_concepts_and_english_connectors(self):
        response = self.client.get(
            reverse('api:property-list'),
            {'search': 'house and መታጠቢያ'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], self.property.slug)

    def test_bedroom_and_bathroom_counts_are_structured_filters(self):
        Property.objects.create(
            title='One bathroom property',
            slug='one-bathroom-count-search',
            location='Submitted location',
            property_type='house',
            listing_type=Property.ListingType.SALE,
            price=250000,
            bedrooms=1,
            bathrooms=1,
            description='Available listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

        bathroom_response = self.client.get(
            reverse('api:property-list'),
            {'search': 'bathroom 2'},
        )
        bedroom_response = self.client.get(
            reverse('api:property-list'),
            {'search': '3 bedrooms'},
        )

        self.assertEqual(bathroom_response.data['count'], 1)
        self.assertEqual(bathroom_response.data['results'][0]['slug'], self.property.slug)
        self.assertEqual(bedroom_response.data['count'], 1)
        self.assertEqual(bedroom_response.data['results'][0]['slug'], self.property.slug)

    def test_english_amenity_search_uses_the_existing_amenity_relation(self):
        response = self.client.get(
            reverse('api:property-list'),
            {'search': 'garden'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], self.property.slug)

    def test_location_alias_search_and_suggestions_resolve_the_same_location(self):
        country = Location.objects.create(
            name='Test Country',
            slug='test-country-search',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Test City Administration',
            slug='test-city-administration-search',
            location_type=Location.Type.CITY_ADMINISTRATION,
            parent=country,
        )
        subcity = Location.objects.create(
            name='Test Subcity',
            slug='test-subcity-search',
            aliases_am=['የሙከራ አካባቢ'],
            location_type=Location.Type.SUBCITY,
            parent=city,
        )
        self.property.administrative_location = subcity
        self.property.save(update_fields=['administrative_location'])

        property_response = self.client.get(
            reverse('api:property-list'),
            {'search': 'የሙከራ አካባቢ'},
        )
        location_response = self.client.get(
            reverse('api:location-list'),
            {'search': 'የሙከራ'},
        )

        self.assertEqual(property_response.data['count'], 1)
        self.assertEqual(property_response.data['results'][0]['slug'], self.property.slug)
        self.assertEqual([item['id'] for item in location_response.data], [subcity.id])

    def test_search_combines_location_price_and_listing_type_filters(self):
        country = Location.objects.create(
            name='Test Country Combined',
            slug='test-country-combined-search',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Test City Administration Combined',
            slug='test-city-administration-combined',
            location_type=Location.Type.CITY_ADMINISTRATION,
            parent=country,
        )
        self.property.administrative_location = city
        self.property.save(update_fields=['administrative_location'])

        response = self.client.get(
            reverse('api:property-list'),
            {
                'search': 'bathroom',
                'location_id': city.id,
                'listing_type': 'sale',
                'min_price': '400000',
                'max_price': '600000',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], self.property.slug)

    def test_bathroom_search_preserves_pagination_and_price_sorting(self):
        Property.objects.create(
            title='Lower priced bathroom property',
            slug='lower-priced-bathroom-property',
            location='Submitted location',
            property_type='apartment',
            listing_type=Property.ListingType.RENT,
            price=100000,
            rental_frequency=Property.RentalFrequency.MONTHLY,
            bathrooms=1,
            description='Available apartment.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        Property.objects.create(
            title='Higher priced bathroom rental property',
            slug='higher-priced-bathroom-rental-property',
            location='Submitted location',
            property_type='apartment',
            listing_type=Property.ListingType.RENT,
            price=200000,
            rental_frequency=Property.RentalFrequency.MONTHLY,
            bathrooms=1,
            description='Available apartment.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

        response = self.client.get(
            reverse('api:property-list'),
            {'search': 'bathroom', 'listing_type': 'rent', 'ordering': 'price', 'page_size': 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(response.data['results'][0]['slug'], 'lower-priced-bathroom-property')

    def test_unknown_amharic_search_is_safe_and_does_not_match_unrelated_listings(self):
        response = self.client.get(
            reverse('api:property-list'),
            {'search': 'ጽሑፍ ያልታወቀ'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

    def test_location_alias_serializer_normalizes_unicode_and_duplicate_terms(self):
        serializer = LocationSerializer(data={
            'name': 'Test Location',
            'slug': 'test-location',
            'location_type': Location.Type.COUNTRY,
            'parent': None,
            'aliases_en': ['  Test   Place ', 'test place'],
            'aliases_am': [' መታጠቢያ '],
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['aliases_en'], ['test place'])
        self.assertEqual(serializer.validated_data['aliases_am'], ['መታጠቢያ'])

    def test_search_query_count_is_bounded_as_matching_results_grow(self):
        for index in range(8):
            Property.objects.create(
                title=f'Additional bathroom property {index}',
                slug=f'additional-bathroom-property-{index}',
                location='Submitted location',
                property_type='house',
                listing_type=Property.ListingType.SALE,
                price=300000 + index,
                bathrooms=1,
                description='Available listing.',
                status=Property.Status.AVAILABLE,
                publication_status=Property.PublicationStatus.PUBLISHED,
            )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                reverse('api:property-list'),
                {'search': 'bathroom', 'page_size': 20},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 9)
        self.assertLessEqual(len(queries), 20)

    def test_invalid_filter_returns_consistent_validation_error(self):
        response = self.client.get(
            reverse('api:property-list'),
            {'min_price': 'not-a-price'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['status_code'], 400)
        self.assertIn('min_price', response.data['error']['details'])

    def test_public_list_hides_unavailable_or_unpublished_properties(self):
        Property.objects.create(
            title='Sold listing',
            slug='sold-listing-api',
            location='Submitted location',
            price=100000,
            description='Not available.',
            status=Property.Status.SOLD,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        Property.objects.create(
            title='Pending listing',
            slug='pending-listing-api',
            location='Submitted location',
            price=200000,
            description='Not published.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PENDING_REVIEW,
        )
        Property.objects.create(
            title='Inactive listing',
            slug='inactive-listing-api',
            location='Submitted location',
            price=250000,
            description='Not currently available.',
            status=Property.Status.INACTIVE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        Property.objects.create(
            title='Suspended listing',
            slug='suspended-listing-api',
            location='Submitted location',
            price=300000,
            description='Temporarily suspended.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.SUSPENDED,
        )
        Property.objects.create(
            title='Expired listing',
            slug='expired-listing-api',
            location='Submitted location',
            price=350000,
            description='Expired listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.EXPIRED,
        )
        Property.objects.create(
            title='Withdrawn listing',
            slug='withdrawn-listing-api',
            location='Submitted location',
            price=400000,
            description='Withdrawn listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.WITHDRAWN,
        )

        response = self.client.get(reverse('api:property-list'))

        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], self.property.slug)

    def test_detail_never_exposes_property_contact_and_includes_localized_amenity_fields(self):
        self.property.contact_phone = '+251900000000'
        self.property.contact_email = 'contact@example.com'
        self.property.contact_publicly_visible = True
        self.property.save()

        response = self.client.get(
            reverse('api:property-detail', kwargs={'slug': self.property.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('contact_name', response.data)
        self.assertNotIn('contact_phone', response.data)
        self.assertNotIn('contact_email', response.data)
        self.assertEqual(response.data['amenities'][0]['slug'], 'garden')
        self.assertEqual(response.data['currency'], 'ETB')

    def test_detail_does_not_expose_private_contact_by_default(self):
        self.property.contact_name = 'Private owner'
        self.property.contact_phone = '+251900000000'
        self.property.contact_email = 'private@example.com'
        self.property.save()

        response = self.client.get(
            reverse('api:property-detail', kwargs={'slug': self.property.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('contact_name', response.data)
        self.assertNotIn('contact_phone', response.data)
        self.assertNotIn('contact_email', response.data)

    def test_public_property_responses_never_expose_gps_coordinates(self):
        self.property.latitude = Decimal('9.035812')
        self.property.longitude = Decimal('38.752432')
        self.property.save(update_fields=['latitude', 'longitude'])

        detail = self.client.get(reverse('api:property-detail', kwargs={'slug': self.property.slug}))
        public_list = self.client.get(reverse('api:property-list'))
        listed_location = public_list.data['results'][0]

        self.assertEqual(detail.status_code, 200)
        self.assertNotIn('latitude', detail.data)
        self.assertNotIn('longitude', detail.data)
        self.assertNotIn('latitude', listed_location)
        self.assertNotIn('longitude', listed_location)

    def test_detail_does_not_expose_unavailable_property(self):
        self.property.status = Property.Status.RENTED
        self.property.listing_type = Property.ListingType.RENT
        self.property.save()

        response = self.client.get(
            reverse('api:property-detail', kwargs={'slug': self.property.slug})
        )

        self.assertEqual(response.status_code, 404)

    def test_pagination_can_be_changed_within_configured_limit(self):
        Property.objects.create(
            title='Second available house',
            slug='second-available-house-api',
            location='Submitted location',
            price=700000,
            description='A second listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

        response = self.client.get(reverse('api:property-list'), {'page_size': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 1)


class ManagedPropertyApiTests(APITestCase):
    def setUp(self):
        self.country = Location.objects.create(
            name='Test Country Managed',
            slug='test-country-managed',
            location_type=Location.Type.COUNTRY,
        )
        self.city = Location.objects.create(
            name='Test City Managed',
            slug='test-city-managed',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        self.subcity = Location.objects.create(
            name='Test Subcity Managed',
            slug='test-subcity-managed',
            location_type=Location.Type.SUBCITY,
            parent=self.city,
        )
        self.other_city = Location.objects.create(
            name='Other Test City Managed',
            slug='other-test-city-managed',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        self.other_subcity = Location.objects.create(
            name='Other Test Subcity Managed',
            slug='other-test-subcity-managed',
            location_type=Location.Type.SUBCITY,
            parent=self.other_city,
        )
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username='crud-owner')
        Profile.objects.create(user=self.owner, role=Profile.Role.OWNER)
        self.other_owner = user_model.objects.create_user(username='other-owner')
        Profile.objects.create(user=self.other_owner, role=Profile.Role.OWNER)
        self.customer = user_model.objects.create_user(username='listing-customer')
        Profile.objects.create(user=self.customer, role=Profile.Role.CUSTOMER)
        self.manager = user_model.objects.create_user(username='listing-broker')
        Profile.objects.create(
            user=self.manager,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=self.city,
            management_permissions=[
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            ],
        )
        self.property = Property.objects.create(
            title='Owner property',
            slug='owner-property-api',
            location='Submitted location',
            administrative_location=self.subcity,
            price=400000,
            description='Owner listing.',
            owner=self.owner,
            submitted_by=self.manager,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        PropertyBrokerAssignment.objects.create(property=self.property, broker=self.manager)

    def property_payload(self, **overrides):
        payload = {
            'title': 'New owner listing',
            'location': 'Submitted location',
            'administrative_location': self.subcity.pk,
            'category': 'house',
            'listing_type': 'sale',
            'price': '350000.00',
            'bedrooms': 3,
            'bathrooms': 2,
            'area_sqft': 1400,
            'description': 'New listing submitted by its owner.',
            'contact_phone': '+251900000000',
        }
        payload.update(overrides)
        return payload

    def test_broker_can_create_in_assigned_subcity_and_gets_only_its_viewing_assignment(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        created_property = Property.objects.get(pk=response.data['id'])
        self.assertEqual(created_property.administrative_location, self.subcity)
        self.assertTrue(
            PropertyBrokerAssignment.objects.filter(
                property=created_property,
                broker=self.manager,
            ).exists()
        )

    def test_managed_listing_includes_images_for_broker_card_view(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(reverse('api:managed-property-list'))

        self.assertEqual(response.status_code, 200)
        listing = next(item for item in response.data['results'] if item['id'] == self.property.pk)
        self.assertEqual(listing['images'], [])

    def test_broker_cannot_create_or_access_property_outside_assigned_city(self):
        outside_property = Property.objects.create(
            title='Outside city property',
            slug='outside-city-managed-property',
            location='Outside city',
            administrative_location=self.other_subcity,
            price=250000,
            description='A listing in another city.',
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        self.client.force_authenticate(user=self.manager)

        rejected_create = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(
                title='Cross-city listing',
                administrative_location=self.other_subcity.pk,
            ),
            format='json',
        )
        hidden_detail = self.client.get(
            reverse('api:managed-property-detail', kwargs={'pk': outside_property.pk})
        )

        self.assertEqual(rejected_create.status_code, 400)
        self.assertIn('administrative_location', rejected_create.data['error']['details'])
        self.assertEqual(hidden_detail.status_code, 404)

    def test_property_owner_cannot_manage_listings_from_ownership_alone(self):
        self.client.force_authenticate(user=self.owner)
        create = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(),
            format='json',
        )
        listed = self.client.get(reverse('api:managed-property-list'))

        self.assertEqual(create.status_code, 403)
        self.assertEqual(listed.status_code, 403)

    def test_property_owner_cannot_edit_even_owned_properties_without_management_permission(self):
        Property.objects.create(
            title='Other owner listing',
            slug='other-owner-listing-api',
            location='Submitted location',
            price=200000,
            description='Not accessible to this owner.',
            owner=self.other_owner,
        )
        self.client.force_authenticate(user=self.owner)

        listed = self.client.get(reverse('api:managed-property-list'))
        denied_detail = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {'title': 'Unauthorized update'},
            format='json',
        )

        self.assertEqual(listed.status_code, 403)
        self.assertEqual(denied_detail.status_code, 403)

    def test_listing_status_and_type_must_be_compatible(self):
        self.client.force_authenticate(user=self.manager)

        invalid = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {'status': 'rented'},
            format='json',
        )
        valid = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {
                'listing_type': 'rent',
                'status': 'rented',
                'rental_frequency': Property.RentalFrequency.MONTHLY,
            },
            format='json',
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertIn('status', invalid.data['error']['details'])
        self.assertEqual(valid.status_code, 200)
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, Property.Status.RENTED)
        self.assertEqual(self.property.publication_status, Property.PublicationStatus.PUBLISHED)
        public_detail = self.client.get(
            reverse('api:property-detail', kwargs={'slug': self.property.slug})
        )
        self.assertEqual(public_detail.status_code, 404)

    def test_edit_preserves_creation_time_and_updates_listing_fields(self):
        amenity = Amenity.objects.create(name='Managed listing amenity')
        original_created_at = self.property.created_at
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {
                'title': 'Updated managed listing',
                'description': 'Updated description.',
                'price': '425000.00',
                'administrative_location': self.subcity.pk,
                'amenities': [amenity.pk],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.property.refresh_from_db()
        self.assertEqual(self.property.title, 'Updated managed listing')
        self.assertEqual(self.property.description, 'Updated description.')
        self.assertEqual(self.property.price, Decimal('425000.00'))
        self.assertEqual(self.property.administrative_location_id, self.subcity.pk)
        self.assertEqual(list(self.property.amenities.values_list('pk', flat=True)), [amenity.pk])
        self.assertEqual(self.property.created_at, original_created_at)
        self.assertGreater(self.property.updated_at, original_created_at)

    def test_inactive_listing_can_be_reactivated_without_republication(self):
        self.client.force_authenticate(user=self.manager)
        detail_url = reverse('api:managed-property-detail', kwargs={'pk': self.property.pk})
        public_url = reverse('api:property-detail', kwargs={'slug': self.property.slug})

        inactive = self.client.patch(
            detail_url,
            {'status': Property.Status.INACTIVE},
            format='json',
        )
        hidden = self.client.get(public_url)
        self.property.refresh_from_db()
        reactivated = self.client.patch(
            detail_url,
            {'status': Property.Status.AVAILABLE},
            format='json',
        )
        visible = self.client.get(public_url)

        self.assertEqual(inactive.status_code, 200)
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(self.property.publication_status, Property.PublicationStatus.PUBLISHED)
        self.assertEqual(reactivated.status_code, 200)
        self.assertEqual(visible.status_code, 200)

    def test_authorized_manager_cannot_submit_gps_coordinates(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {
                'latitude': '9.035812',
                'longitude': '38.752432',
                'exact_location_is_public': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('latitude', response.data['error']['details'])
        self.assertIn('longitude', response.data['error']['details'])
        self.assertIn('exact_location_is_public', response.data['error']['details'])
        self.property.refresh_from_db()
        self.assertIsNone(self.property.latitude)
        self.assertIsNone(self.property.longitude)
        self.assertFalse(self.property.exact_location_is_public)

    def test_unauthorized_owner_cannot_edit_property_location(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {
                'latitude': '9.035812',
                'longitude': '38.752432',
                'exact_location_is_public': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.property.refresh_from_db()
        self.assertIsNone(self.property.latitude)
        self.assertIsNone(self.property.longitude)

    def test_only_brokers_can_publish_available_properties(self):
        self.property.publication_status = Property.PublicationStatus.DRAFT
        self.property.save(update_fields=['publication_status'])
        publication_url = reverse('api:managed-property-publication', kwargs={'pk': self.property.pk})

        self.client.force_authenticate(user=self.owner)
        forbidden = self.client.post(
            publication_url,
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )
        django_admin = get_user_model().objects.create_superuser(username='listing-django-admin')
        self.client.force_authenticate(user=django_admin)
        administrator_published = self.client.post(
            publication_url,
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )
        broker = get_user_model().objects.create_user(username='listing-moderation-broker')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=self.city,
        )
        self.client.force_authenticate(user=broker)
        published = self.client.post(
            publication_url,
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(administrator_published.status_code, 200)
        self.assertEqual(published.status_code, 403)
        self.property.refresh_from_db()
        self.assertEqual(self.property.publication_status, Property.PublicationStatus.PUBLISHED)

        self.property.status = Property.Status.SOLD
        self.property.save(update_fields=['status'])
        unavailable = self.client.post(
            publication_url,
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )
        self.assertEqual(unavailable.status_code, 403)

    def test_invalid_price_is_rejected_before_database_write(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(price='0'),
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('price', response.data['error']['details'])
        self.assertFalse(Property.objects.filter(title='New owner listing').exists())

    def test_new_rentals_require_daily_monthly_or_yearly_frequency(self):
        self.client.force_authenticate(user=self.manager)
        create_url = reverse('api:managed-property-list')

        missing_period = self.client.post(
            create_url,
            self.property_payload(title='Rental without period', listing_type='rent'),
            format='json',
        )
        weekly_period = self.client.post(
            create_url,
            self.property_payload(
                title='New weekly rental',
                listing_type='rent',
                rental_frequency='weekly',
            ),
            format='json',
        )
        self.assertEqual(missing_period.status_code, 400)
        self.assertIn('rental_frequency', missing_period.data['error']['details'])
        self.assertEqual(weekly_period.status_code, 400)
        self.assertIn('rental_frequency', weekly_period.data['error']['details'])

        for frequency in ('daily', 'monthly', 'yearly'):
            response = self.client.post(
                create_url,
                self.property_payload(
                    title=f'{frequency.title()} rental',
                    listing_type='rent',
                    rental_frequency=frequency,
                ),
                format='json',
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data['rental_frequency'], frequency)
            self.assertIn(response.data['slug'], [
                item['slug']
                for item in self.client.get(reverse('api:property-list')).data['results']
            ])

    def test_legacy_weekly_rental_can_be_edited_without_changing_its_period(self):
        legacy_rental = Property.objects.create(
            title='Legacy weekly rental',
            slug='legacy-weekly-rental',
            location='Submitted location',
            administrative_location=self.subcity,
            listing_type=Property.ListingType.RENT,
            rental_frequency=Property.RentalFrequency.WEEKLY,
            price=1000,
            description='Legacy rental period remains readable.',
            submitted_by=self.manager,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        PropertyBrokerAssignment.objects.create(property=legacy_rental, broker=self.manager)
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': legacy_rental.pk}),
            {'description': 'Updated while preserving legacy period.'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        legacy_rental.refresh_from_db()
        self.assertEqual(legacy_rental.rental_frequency, Property.RentalFrequency.WEEKLY)

    def test_authorized_broker_can_create_property_without_coordinates(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(publication_status='draft'),
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        created = Property.objects.get(pk=response.data['id'])
        self.assertEqual(created.administrative_location_id, self.subcity.pk)
        self.assertIsNone(created.latitude)
        self.assertIsNone(created.longitude)
        self.assertEqual(created.publication_status, Property.PublicationStatus.PUBLISHED)
        public_list = self.client.get(reverse('api:property-list'))
        self.assertIn(created.slug, [item['slug'] for item in public_list.data['results']])

        unavailable = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(title='Inactive manager listing', status='inactive'),
            format='json',
        )
        self.assertEqual(unavailable.status_code, 201)
        self.assertEqual(unavailable.data['publication_status'], Property.PublicationStatus.PUBLISHED)
        refreshed_public_list = self.client.get(reverse('api:property-list'))
        self.assertNotIn(
            unavailable.data['slug'],
            [item['slug'] for item in refreshed_public_list.data['results']],
        )

    def test_property_creation_requires_an_active_city_location(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(administrative_location=None),
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('administrative_location', response.data['error']['details'])
        self.assertFalse(Property.objects.filter(title='New owner listing').exists())

    def test_broker_must_select_a_subcity_not_the_assigned_city(self):
        self.client.force_authenticate(user=self.manager)

        city_only = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(administrative_location=self.city.pk),
            format='json',
        )
        selected_subcity = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(
                title='Subcity-managed listing',
                administrative_location=self.subcity.pk,
            ),
            format='json',
        )

        self.assertEqual(city_only.status_code, 400)
        self.assertIn('administrative_location', city_only.data['error']['details'])
        self.assertEqual(selected_subcity.status_code, 201)

    def test_broker_cannot_create_a_listing_outside_its_assigned_city_hierarchy(self):
        administration = Location.objects.create(
            name='Test City Administration With Subcities',
            slug='test-city-administration-with-subcities',
            location_type=Location.Type.CITY_ADMINISTRATION,
            parent=self.country,
        )
        subcity = Location.objects.create(
            name='Test Kifle Ketema',
            slug='test-kifle-ketema',
            location_type=Location.Type.SUBCITY,
            parent=administration,
        )
        self.client.force_authenticate(user=self.manager)

        city_only = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(administrative_location=administration.pk),
            format='json',
        )
        selected_subcity = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(
                title='Test Kifle Ketema listing',
                administrative_location=subcity.pk,
            ),
            format='json',
        )

        self.assertEqual(city_only.status_code, 400)
        self.assertIn('administrative_location', city_only.data['error']['details'])
        self.assertEqual(selected_subcity.status_code, 400)
    def test_administrator_can_create_listing_without_a_manual_permission_list(self):
        restricted_admin = get_user_model().objects.create_user(
            username='listing-editor-without-moderation',
            is_staff=True,
        )
        Profile.objects.create(
            user=restricted_admin,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.PROPERTY_EDIT_ALL],
        )
        self.client.force_authenticate(user=restricted_admin)

        response = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(title='Must not be published'),
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Property.objects.filter(title='Must not be published').exists())

    def test_broker_can_manage_own_listing_but_not_another_brokers_listing(self):
        broker = get_user_model().objects.create_user(
            username='crud-broker',
            email='crud-broker@example.com',
        )
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=self.city,
            phone='+251911222333',
            management_permissions=[
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            ],
        )
        self.client.force_authenticate(user=broker)

        created = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(title='Broker listing', contact_phone='', contact_email=''),
            format='json',
        )
        update = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': created.data['id']}),
            {'description': 'Updated by the listing agent.'},
            format='json',
        )
        other_broker_update = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {'status': 'inactive'},
            format='json',
        )

        self.assertEqual(update.status_code, 200)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(other_broker_update.status_code, 404)
        self.assertEqual(created.data['publication_status'], Property.PublicationStatus.PUBLISHED)
        self.assertEqual(created.data['contact_phone'], broker.profile.phone)
        self.assertEqual(created.data['contact_email'], broker.email)
        public_list = self.client.get(reverse('api:property-list'))
        public_listing = next(item for item in public_list.data['results'] if item['slug'] == created.data['slug'])
        self.assertEqual(public_listing['public_contact_phone'], broker.profile.phone)
        self.assertEqual(public_listing['public_contact_email'], broker.email)

    def test_registered_customer_cannot_create_or_manage_submitted_listings(self):
        self.client.force_authenticate(user=self.customer)

        created = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(title='Customer submitted draft'),
            format='json',
        )
        response = self.client.get(reverse('api:managed-property-list'))
        denied = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {'title': 'Not my property'},
            format='json',
        )

        self.assertEqual(created.status_code, 403)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(denied.status_code, 403)

    def test_public_visitor_cannot_create_or_publish_a_property(self):
        response = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(title='Public visitor listing'),
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Property.objects.filter(title='Public visitor listing').exists())

    def test_delete_removes_managed_property(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.delete(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk})
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Property.objects.filter(pk=self.property.pk).exists())


class ManagedLocationApiTests(APITestCase):
    def setUp(self):
        self.customer = get_user_model().objects.create_user(username='location-customer')
        Profile.objects.create(user=self.customer, role=Profile.Role.CUSTOMER)
        self.location_admin = get_user_model().objects.create_user(
            username='location-admin',
            email='location-admin@example.com',
            password='test-password',
        )
        Profile.objects.create(
            user=self.location_admin,
            role=Profile.Role.ADMINISTRATOR,
        )
        self.location_admin.is_staff = True
        self.location_admin.save(update_fields=['is_staff'])
        self.country = Location.objects.create(
            name='Ethiopia',
            slug='ethiopia-managed-locations',
            location_type=Location.Type.COUNTRY,
        )

    def test_customer_cannot_read_or_create_managed_locations(self):
        self.client.force_authenticate(user=self.customer)

        listed = self.client.get(reverse('api:managed-location-list'))
        created = self.client.post(
            reverse('api:managed-location-list'),
            {'name': 'Unauthorized Location', 'location_type': 'country'},
            format='json',
        )

        self.assertEqual(listed.status_code, 403)
        self.assertEqual(created.status_code, 403)
        self.assertFalse(Location.objects.filter(name='Unauthorized Location').exists())

    def test_location_manager_list_returns_all_locations_as_an_array(self):
        self.client.force_authenticate(user=self.location_admin)

        response = self.client.get(reverse('api:managed-location-list'), {'all': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Ethiopia')
        self.assertNotIn('latitude', response.data[0])
        self.assertNotIn('longitude', response.data[0])

    def test_location_api_rejects_gps_coordinates(self):
        self.client.force_authenticate(user=self.location_admin)

        response = self.client.post(
            reverse('api:managed-location-list'),
            {
                'name': 'Location without coordinates',
                'latitude': '9.035812',
                'longitude': '38.752432',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('latitude', response.data['error']['details'])
        self.assertIn('longitude', response.data['error']['details'])
        self.assertFalse(Location.objects.filter(name='Location without coordinates').exists())

    def test_location_manager_can_create_and_update_locations_with_audit_records(self):
        self.client.force_authenticate(user=self.location_admin)
        create_response = self.client.post(
            reverse('api:managed-location-list'),
            {
                'name': 'Verified Location',
                'name_am': 'የተረጋገጠ አካባቢ',
                'is_active': True,
                'display_order': 1,
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, 201, create_response.data)
        location_id = create_response.data['id']
        self.assertEqual(create_response.data['location_type'], Location.Type.CITY)
        self.assertEqual(create_response.data['parent_id'], self.country.pk)
        update_response = self.client.patch(
            reverse('api:managed-location-detail', kwargs={'pk': location_id}),
            {'display_order': 2},
            format='json',
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data['display_order'], 2)
        self.assertEqual(
            AdminAuditEvent.objects.filter(object_type='location', object_id=str(location_id)).count(),
            2,
        )

    def test_administrator_can_create_cities_but_not_subcities(self):
        self.client.force_authenticate(user=self.location_admin)

        created_city = self.client.post(
            reverse('api:managed-location-list'),
            {
                'name': 'Verified Marketplace City',
            },
            format='json',
        )
        rejected_subcity = self.client.post(
            reverse('api:managed-location-list'),
            {
                'name': 'Administrator-created Subcity',
                'location_type': 'subcity',
            },
            format='json',
        )

        self.assertEqual(created_city.status_code, 201, created_city.data)
        self.assertEqual(rejected_subcity.status_code, 400)
        self.assertIn('location_type', rejected_subcity.data['error']['details'])
        self.assertFalse(Location.objects.filter(name='Administrator-created Subcity').exists())

    def test_unused_city_can_be_deleted_and_audited(self):
        location = Location.objects.create(
            name='Retained Location',
            slug='retained-location',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        self.client.force_authenticate(user=self.location_admin)

        response = self.client.delete(
            reverse('api:managed-location-detail', kwargs={'pk': location.pk})
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Location.objects.filter(pk=location.pk).exists())
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='location_deleted',
                object_id=str(location.pk),
            ).exists()
        )

    def test_city_with_a_broker_assignment_cannot_be_deleted(self):
        city = Location.objects.create(
            name='Broker Bound City',
            slug='broker-bound-city',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        broker = get_user_model().objects.create_user(username='city-bound-broker')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            assigned_city=city,
        )
        self.client.force_authenticate(user=self.location_admin)

        response = self.client.delete(
            reverse('api:managed-location-detail', kwargs={'pk': city.pk})
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('assigned to agents', str(response.data))
        self.assertTrue(Location.objects.filter(pk=city.pk).exists())

    def test_active_parent_cannot_be_deactivated_while_descendants_are_active(self):
        country = Location.objects.create(
            name='Parent Location',
            slug='parent-location',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Child City',
            slug='child-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        subcity = Location.objects.create(
            name='Grandchild Subcity',
            slug='grandchild-subcity',
            location_type=Location.Type.SUBCITY,
            parent=city,
        )
        serializer = LocationSerializer(
            instance=city,
            data={'is_active': False},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('is_active', serializer.errors)
        self.assertTrue(subcity.is_active)

    def test_location_manager_can_create_deactivate_and_reorder_a_subcity(self):
        broker_city = Location.objects.create(
            name='Broker Assigned City',
            slug='broker-assigned-city',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        broker_user = get_user_model().objects.create_user(username='subcity-manager')
        Profile.objects.create(
            user=broker_user,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=broker_city,
        )
        self.client.force_authenticate(user=broker_user)

        created = self.client.post(
            reverse('api:managed-location-list'),
            {
                'name': 'Test Subcity Lifecycle',
                'is_active': True,
                'display_order': 1,
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.data)

        updated = self.client.patch(
            reverse('api:managed-location-detail', kwargs={'pk': created.data['id']}),
            {'is_active': False, 'display_order': 4},
            format='json',
        )
        public_children = self.client.get(
            reverse('api:location-list'),
            {'parent_id': broker_city.pk},
        )
        reactivated = self.client.patch(
            reverse('api:managed-location-detail', kwargs={'pk': created.data['id']}),
            {'is_active': True},
            format='json',
        )
        active_children = self.client.get(
            reverse('api:location-list'),
            {'parent_id': broker_city.pk},
        )

        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.data['is_active'])
        self.assertEqual(updated.data['display_order'], 4)
        self.assertEqual(public_children.data, [])
        self.assertEqual(reactivated.status_code, 200)
        self.assertTrue(reactivated.data['is_active'])
        self.assertEqual([item['id'] for item in active_children.data], [created.data['id']])

    def test_broker_location_management_is_limited_to_assigned_city(self):
        assigned_city = Location.objects.create(
            name='Scoped Broker City',
            slug='scoped-broker-city',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        foreign_city = Location.objects.create(
            name='Foreign Broker City',
            slug='foreign-broker-city',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        broker_user = get_user_model().objects.create_user(username='scoped-subcity-manager')
        Profile.objects.create(
            user=broker_user,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=assigned_city,
        )
        self.client.force_authenticate(user=broker_user)

        locations = self.client.get(reverse('api:managed-location-list'), {'all': '1'})
        rejected_create = self.client.post(
            reverse('api:managed-location-list'),
            {
                'name': 'Foreign Subcity',
                'location_type': 'subcity',
                'parent': foreign_city.pk,
            },
            format='json',
        )

        self.assertEqual(locations.status_code, 200)
        self.assertEqual([item['id'] for item in locations.data], [assigned_city.pk])
        self.assertEqual(rejected_create.status_code, 400)
        self.assertIn('parent', rejected_create.data['error']['details'])
        self.assertFalse(Location.objects.filter(name='Foreign Subcity').exists())

    def test_deactivating_a_referenced_location_preserves_existing_public_properties(self):
        country = Location.objects.create(
            name='Test Country Referenced Location',
            slug='test-country-referenced-location',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Test City Referenced Location',
            slug='test-city-referenced-location',
            location_type=Location.Type.CITY,
            parent=country,
        )
        other_city = Location.objects.create(
            name='Test Other City Referenced Location',
            slug='test-other-city-referenced-location',
            location_type=Location.Type.CITY,
            parent=country,
        )
        property_obj = Property.objects.create(
            title='Referenced location property',
            slug='referenced-location-property',
            location='Test City Referenced Location',
            administrative_location=city,
            property_type='house',
            listing_type=Property.ListingType.SALE,
            price=300000,
            description='A published property at a configured location.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        self.client.force_authenticate(user=self.location_admin)

        moved = self.client.patch(
            reverse('api:managed-location-detail', kwargs={'pk': city.pk}),
            {'parent': other_city.pk},
            format='json',
        )
        deactivated = self.client.patch(
            reverse('api:managed-location-detail', kwargs={'pk': city.pk}),
            {'is_active': False},
            format='json',
        )
        public_list = self.client.get(reverse('api:property-list'))
        public_detail = self.client.get(
            reverse('api:property-detail', kwargs={'slug': property_obj.slug})
        )
        public_cities = self.client.get(
            reverse('api:location-list'),
            {'types': 'city,city_administration'},
        )
        city_filter = self.client.get(
            reverse('api:property-list'),
            {'city_id': city.pk},
        )

        self.assertEqual(moved.status_code, 400)
        self.assertIn('parent', moved.data['error']['details'])
        self.assertEqual(deactivated.status_code, 200)
        self.assertIn(property_obj.slug, [item['slug'] for item in public_list.data['results']])
        self.assertEqual(public_detail.status_code, 200)
        self.assertNotIn(city.pk, [item['id'] for item in public_cities.data])
        self.assertEqual(city_filter.data['count'], 0)


class PropertyImageApiTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
            PRIVATE_MEDIA_ROOT=str(Path(self.media_directory.name) / 'private'),
            CLOUDINARY_URL='',
        )
        settings_override.enable()
        self.addCleanup(settings_override.disable)

        country = Location.objects.create(
            name='Image Test Country',
            slug='image-test-country',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Image Test City',
            slug='image-test-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        subcity = Location.objects.create(
            name='Image Test Subcity',
            slug='image-test-subcity',
            location_type=Location.Type.SUBCITY,
            parent=city,
        )
        owner = get_user_model().objects.create_user(username='image-owner')
        Profile.objects.create(user=owner, role=Profile.Role.OWNER)
        broker = get_user_model().objects.create_user(username='image-manager')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=city,
            management_permissions=[Profile.Permission.PROPERTY_MANAGE_ASSIGNED],
        )
        self.other_owner = get_user_model().objects.create_user(username='image-other-owner')
        Profile.objects.create(user=self.other_owner, role=Profile.Role.OWNER)
        self.property = Property.objects.create(
            title='Image test property',
            slug='image-test-property-api',
            location='Submitted location',
            administrative_location=subcity,
            price=400000,
            description='Image test listing.',
            owner=owner,
            submitted_by=broker,
        )
        PropertyBrokerAssignment.objects.create(property=self.property, broker=broker)
        self.client.force_authenticate(user=broker)

    def make_image(self, name='property.png', size=(300, 200), compress_level=6, image_format='PNG'):
        buffer = BytesIO()
        image = Image.new('RGB', size, color='green')
        save_options = {'compress_level': compress_level} if image_format == 'PNG' else {}
        image.save(buffer, format=image_format, **save_options)
        return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{image_format.lower()}')

    def image_url(self):
        return reverse(
            'api:managed-property-images',
            kwargs={'property_id': self.property.pk},
        )

    def test_watermark_places_low_opacity_handle_in_the_center(self):
        image_buffer = BytesIO()
        Image.new('RGB', (600, 400), color=(80, 120, 160)).save(image_buffer, format='PNG')

        with patch(
            'properties.image_processing._branding',
            return_value=('habeshapropertycenter', None, ''),
        ):
            watermarked = watermark_image(ContentFile(image_buffer.getvalue()))

        with Image.open(BytesIO(image_buffer.getvalue())) as original, Image.open(watermarked) as result:
            center = (100, 80, 500, 320)
            difference = ImageChops.difference(
                original.convert('RGB').crop(center),
                result.convert('RGB').crop(center),
            )
            self.assertIsNotNone(difference.getbbox())
            self.assertLess(max(channel[1] for channel in difference.getextrema()), 100)

    def test_upload_validates_image_and_sets_first_image_primary(self):
        response = self.client.post(
            self.image_url(),
            {'image': self.make_image(), 'caption': 'Front view'},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        image = PropertyImage.objects.get(pk=response.data['id'])
        self.assertTrue(image.is_primary)
        self.assertTrue(Path(image.image.path).is_file())
        self.assertTrue(Path(image.original_image.path).is_file())
        self.assertEqual(image.original_content_type, 'image/png')

    def test_public_image_is_watermarked_and_original_is_only_available_to_owner(self):
        uploaded = self.make_image()
        original_bytes = uploaded.read()
        uploaded.seek(0)
        response = self.client.post(
            self.image_url(),
            {'image': uploaded},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.data)
        image = PropertyImage.objects.get(pk=response.data['id'])

        with image.image.open('rb') as public_file:
            public_bytes = public_file.read()
        with image.original_image.open('rb') as original_file:
            self.assertEqual(original_file.read(), original_bytes)
        with Image.open(BytesIO(original_bytes)) as original, Image.open(BytesIO(public_bytes)) as public:
            self.assertEqual(public.size, original.size)
            self.assertNotEqual(public.convert('RGB').tobytes(), original.convert('RGB').tobytes())

        original_url = reverse('api:property-image-original', kwargs={'pk': image.pk})
        allowed = self.client.get(original_url)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed['Cache-Control'], 'private, no-store')
        self.assertEqual(b''.join(allowed.streaming_content), original_bytes)

        self.client.force_authenticate(user=self.other_owner)
        denied = self.client.get(original_url)
        self.assertEqual(denied.status_code, 404)

    def test_metadata_update_does_not_watermark_an_existing_image_again(self):
        self.client.post(
            self.image_url(),
            {'image': self.make_image()},
            format='multipart',
        )
        image = PropertyImage.objects.get(property=self.property)
        with image.image.open('rb') as public_file:
            public_before = public_file.read()
        with image.original_image.open('rb') as original_file:
            original_before = original_file.read()

        image.caption = 'Updated caption'
        image.save(update_fields=['caption'])

        with image.image.open('rb') as public_file:
            self.assertEqual(public_file.read(), public_before)
        with image.original_image.open('rb') as original_file:
            self.assertEqual(original_file.read(), original_before)

    def test_existing_image_watermark_command_preserves_original_and_is_idempotent(self):
        uploaded = self.make_image(name='legacy.png')
        original_bytes = uploaded.read()
        uploaded.seek(0)
        legacy_name = PropertyImage._meta.get_field('image').storage.save(
            'property_images/legacy.png',
            ContentFile(original_bytes),
        )
        image = PropertyImage.objects.create(property=self.property, image=legacy_name)

        with self.captureOnCommitCallbacks(execute=True):
            call_command('watermark_property_images')
        image.refresh_from_db()

        self.assertNotEqual(image.image.name, legacy_name)
        with image.original_image.open('rb') as original_file:
            self.assertEqual(original_file.read(), original_bytes)
        with image.image.open('rb') as public_file:
            public_bytes = public_file.read()
        with Image.open(BytesIO(original_bytes)) as original, Image.open(BytesIO(public_bytes)) as public:
            self.assertEqual(public.size, original.size)
            self.assertNotEqual(public.convert('RGB').tobytes(), original.convert('RGB').tobytes())

        with patch(
            'properties.image_processing._branding',
            return_value=('habeshapropertycenter', None, '+251911222333'),
        ):
            call_command('watermark_property_images', '--refresh')
        image.refresh_from_db()
        with image.image.open('rb') as public_file:
            phone_watermarked_bytes = public_file.read()
        with image.original_image.open('rb') as original_file:
            self.assertEqual(original_file.read(), original_bytes)
        self.assertNotEqual(phone_watermarked_bytes, public_bytes)

        call_command('watermark_property_images')
        image.refresh_from_db()
        self.assertEqual(image.original_filename, 'legacy.png')

    def test_upload_accepts_supported_image_formats_and_stores_files_under_media_root(self):
        format_extensions = (
            ('PNG', 'png'),
            ('JPEG', 'jpg'),
            ('JPEG', 'jpeg'),
            ('WEBP', 'webp'),
        )
        responses = [
            self.client.post(
                self.image_url(),
                {'image': self.make_image(name=f'property.{extension}', image_format=image_format)},
                format='multipart',
            )
            for image_format, extension in format_extensions
        ]

        self.assertEqual([response.status_code for response in responses], [201] * len(format_extensions))
        for response in responses:
            image = PropertyImage.objects.get(pk=response.data['id'])
            self.assertTrue(Path(image.image.path).is_file())
            self.assertEqual(Path(image.image.path).parent, Path(self.media_directory.name) / 'property_images')

    def test_changing_images_keeps_a_published_property_public(self):
        self.property.publication_status = Property.PublicationStatus.PUBLISHED
        self.property.save(update_fields=['publication_status'])

        response = self.client.post(
            self.image_url(),
            {'image': self.make_image(), 'caption': 'Updated image'},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.property.refresh_from_db()
        self.assertEqual(self.property.publication_status, Property.PublicationStatus.PUBLISHED)
        public_detail = self.client.get(
            reverse('api:property-detail', kwargs={'slug': self.property.slug})
        )
        self.assertEqual(public_detail.status_code, 200)

    def test_invalid_file_extension_is_rejected(self):
        response = self.client.post(
            self.image_url(),
            {
                'image': SimpleUploadedFile('document.txt', b'not an image', content_type='text/plain'),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.data['error']['details'])

    def test_invalid_image_content_is_rejected_with_an_allowed_extension(self):
        response = self.client.post(
            self.image_url(),
            {
                'image': SimpleUploadedFile(
                    'not-an-image.png',
                    b'not actually a PNG image',
                    content_type='image/png',
                ),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.data['error']['details'])
        self.assertFalse(PropertyImage.objects.filter(property=self.property).exists())

    def test_image_larger_than_ten_megabytes_is_rejected(self):
        oversized_image = self.make_image(
            name='oversized.png',
            size=(2000, 2000),
            compress_level=0,
        )
        self.assertGreater(oversized_image.size, 10 * 1024 * 1024)

        response = self.client.post(
            self.image_url(),
            {'image': oversized_image},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('10 MB or smaller', str(response.data['error']['details']))

    def test_setting_a_new_primary_image_demotes_the_previous_one(self):
        first = self.client.post(
            self.image_url(),
            {'image': self.make_image(name='first.png')},
            format='multipart',
        )
        second = self.client.post(
            self.image_url(),
            {'image': self.make_image(name='second.png'), 'is_primary': True},
            format='multipart',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertFalse(PropertyImage.objects.get(pk=first.data['id']).is_primary)
        self.assertTrue(PropertyImage.objects.get(pk=second.data['id']).is_primary)

    def test_approved_broker_cannot_manage_images_registered_by_another_user(self):
        other_property = Property.objects.create(
            title='Other image property',
            location='Submitted location',
            price=300000,
            description='Not managed by the caller.',
            owner=self.other_owner,
        )

        response = self.client.post(
            reverse('api:managed-property-images', kwargs={'property_id': other_property.pk}),
            {'image': self.make_image()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 404)

    def test_image_can_be_deleted_with_its_stored_file(self):
        upload = self.client.post(
            self.image_url(),
            {'image': self.make_image()},
            format='multipart',
        )
        image = PropertyImage.objects.get(pk=upload.data['id'])
        stored_path = Path(image.image.path)
        original_path = Path(image.original_image.path)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(
                reverse(
                    'api:managed-property-image-detail',
                    kwargs={'property_id': self.property.pk, 'pk': image.pk},
                )
            )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(PropertyImage.objects.filter(pk=image.pk).exists())
        self.assertFalse(stored_path.exists())
        self.assertFalse(original_path.exists())

    def test_deleting_property_removes_its_stored_images(self):
        upload = self.client.post(
            self.image_url(),
            {'image': self.make_image()},
            format='multipart',
        )
        image = PropertyImage.objects.get(pk=upload.data['id'])
        stored_path = Path(image.image.path)
        original_path = Path(image.original_image.path)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(
                reverse('api:managed-property-detail', kwargs={'pk': self.property.pk})
            )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Property.objects.filter(pk=self.property.pk).exists())
        self.assertFalse(stored_path.exists())
        self.assertFalse(original_path.exists())

    def test_image_limit_is_enforced(self):
        for index in range(10):
            self.property.images.create(image=self.make_image(name=f'image-{index}.png'))

        response = self.client.post(
            self.image_url(),
            {'image': self.make_image(name='eleventh.png')},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.data['error']['details'])
        self.assertEqual(self.property.images.count(), 10)
