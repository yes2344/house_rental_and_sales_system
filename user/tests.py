import hashlib
from io import StringIO
import os
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from admin.models import BrokerageSettings
from user.models import Property, ViewingRequest


class DemoAdminBootstrapCommandTests(TestCase):
    def test_command_skips_when_no_credentials_are_configured(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in (
                'DJANGO_SUPERUSER_USERNAME',
                'DJANGO_SUPERUSER_EMAIL',
                'DJANGO_SUPERUSER_PASSWORD',
            ):
                os.environ.pop(key, None)
            call_command('ensure_demo_admin', stdout=StringIO())

        self.assertFalse(get_user_model().objects.exists())

    def test_command_requires_all_credentials(self):
        with patch.dict(
            os.environ,
            {
                'DJANGO_SUPERUSER_USERNAME': 'demo-admin',
                'DJANGO_SUPERUSER_EMAIL': '',
                'DJANGO_SUPERUSER_PASSWORD': 'Strong-Demo-Password-39!',
            },
        ):
            with self.assertRaises(CommandError):
                call_command('ensure_demo_admin')

    def test_command_creates_superuser_once_without_resetting_password(self):
        credentials = {
            'DJANGO_SUPERUSER_USERNAME': 'demo-admin',
            'DJANGO_SUPERUSER_EMAIL': 'demo-admin@example.com',
            'DJANGO_SUPERUSER_PASSWORD': 'Strong-Demo-Password-39!',
        }
        with patch.dict(os.environ, credentials):
            call_command('ensure_demo_admin', stdout=StringIO())
            user = get_user_model().objects.get(username='demo-admin')
            original_password_hash = user.password

            os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'A-New-Password-948!'
            call_command('ensure_demo_admin', stdout=StringIO())

        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.email, 'demo-admin@example.com')
        self.assertEqual(user.password, original_password_hash)

    def test_command_refuses_to_promote_an_existing_non_superuser(self):
        get_user_model().objects.create_user(username='demo-admin', password='safe-test-password')
        credentials = {
            'DJANGO_SUPERUSER_USERNAME': 'demo-admin',
            'DJANGO_SUPERUSER_EMAIL': 'demo-admin@example.com',
            'DJANGO_SUPERUSER_PASSWORD': 'Strong-Demo-Password-39!',
        }
        with patch.dict(os.environ, credentials):
            with self.assertRaises(CommandError):
                call_command('ensure_demo_admin')


class ViewingRequestApprovalTests(TestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_user(
            username='viewing-test-admin',
            password='SecurePass123!value',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin_user)
        self.receipt_token = 'visitor-private-receipt-token'
        self.property = Property.objects.create(
            title='Approval Test Property',
            slug='approval-test-property',
            location='Town Center',
            property_type='house',
            price=250000,
            bedrooms=3,
            bathrooms=2,
            area_sqft=1800,
            description='Nice property',
            features='Garden',
            status='active',
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        self.request_obj = ViewingRequest.objects.create(
            property=self.property,
            full_name='Test Buyer',
            email='buyer@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=3),
            preferred_time='10:30:00',
            message='I want to visit',
            status='pending',
            receipt_token_digest=hashlib.sha256(self.receipt_token.encode()).hexdigest(),
        )

    def test_legacy_admin_portal_has_no_viewing_request_management_route(self):
        with self.assertRaises(NoReverseMatch):
            reverse('admin_viewing_update', args=[self.request_obj.pk])

    def test_legacy_public_form_returns_a_one_time_receipt_token(self):
        response = self.client.post(
            reverse('user_property_request', args=[self.property.pk]),
            {
                'full_name': 'Guest Visitor',
                'email': 'guest@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=2)).isoformat(),
                'message': 'Please contact me.',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/viewing_request_receipt.html')
        viewing = ViewingRequest.objects.exclude(pk=self.request_obj.pk).get()
        self.assertTrue(viewing.receipt_token_digest)
        self.assertContains(response, 'Keep this private receipt token')
        self.assertContains(response, reverse('user_viewing_request_status'))

    def test_legacy_viewing_form_requires_authentication(self):
        self.client.logout()

        response = self.client.post(
            reverse('user_property_request', args=[self.property.pk]),
            {
                'full_name': 'Guest Visitor',
                'email': 'guest@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=2)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ViewingRequest.objects.count(), 1)

    def test_property_can_be_marked_for_sale_or_rent(self):
        rent_property = Property.objects.create(
            title='Rent Property',
            slug='rent-property',
            location='Town Center',
            property_type='house',
            listing_type='rent',
            price=1800,
            bedrooms=2,
            bathrooms=1,
            area_sqft=1200,
            description='Rental home',
            features='Parking',
            status='active',
        )

        self.assertEqual(rent_property.listing_type, 'rent')
        self.assertEqual(rent_property.get_listing_type_display(), 'For Rent')

    def test_active_property_without_featured_flag_appears_on_home_page(self):
        non_featured = Property.objects.create(
            title='Visible Non Featured Home',
            slug='visible-non-featured-home',
            location='Town Center',
            property_type='house',
            price=320000,
            bedrooms=4,
            bathrooms=3,
            area_sqft=2200,
            description='A visible home',
            features='Garden',
            status='active',
            publication_status=Property.PublicationStatus.PUBLISHED,
            is_featured=False,
        )

        response = self.client.get(reverse('user_home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, non_featured.title)

    def test_legacy_public_pages_hide_drafts_and_unavailable_properties(self):
        Property.objects.create(
            title='Unpublished private draft',
            slug='unpublished-private-draft',
            location='Unverified address',
            property_type='house',
            price=320000,
            description='Must not appear publicly.',
            status='active',
            publication_status=Property.PublicationStatus.DRAFT,
        )

        home_response = self.client.get(reverse('user_home'))
        listings_response = self.client.get(reverse('user_listings'))
        detail_response = self.client.get(
            reverse('user_property_detail', args=['unpublished-private-draft'])
        )

        self.assertNotContains(home_response, 'Unpublished private draft')
        self.assertNotContains(listings_response, 'Unpublished private draft')
        self.assertEqual(detail_response.status_code, 404)

    def test_legacy_public_pages_never_show_map_coordinates(self):
        self.property.latitude = Decimal('9.035812')
        self.property.longitude = Decimal('38.752432')
        self.property.exact_location_is_public = True
        self.property.save(update_fields=['latitude', 'longitude', 'exact_location_is_public'])

        home = self.client.get(reverse('user_home'))
        listings = self.client.get(reverse('user_listings'))
        detail = self.client.get(
            reverse('user_property_detail', args=[self.property.slug])
        )

        for response in (home, listings, detail):
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'openstreetmap.org')
            self.assertNotContains(response, 'export/embed.html')
        self.assertContains(home, 'property-location-icon')
        self.assertContains(listings, 'property-location-icon')
        self.assertContains(detail, 'Listed')
        self.assertContains(detail, 'Available')

    def test_legacy_public_footer_uses_configured_brokerage_contacts(self):
        BrokerageSettings.objects.create(
            business_name='Configured Brokerage',
            phone='+251900000000',
            email='brokerage@example.com',
        )

        response = self.client.get(reverse('user_home'))

        self.assertContains(response, 'Configured Brokerage')
        self.assertContains(response, 'tel:+251900000000')
        self.assertContains(response, 'mailto:brokerage@example.com')
