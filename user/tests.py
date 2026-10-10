import hashlib
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from admin.models import BrokerageSettings
from user.models import Property, ViewingRequest
from viewings.models import ViewingRequestEvent


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
        self.proposed_date = timezone.localdate() + timedelta(days=5)
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

    def test_admin_proposes_date_and_visitor_must_accept_to_confirm(self):
        url = reverse('admin_viewing_update', args=[self.request_obj.pk])
        response = self.client.post(
            url,
            {
                'status': 'confirmed',
                'scheduled_date': self.proposed_date.isoformat(),
                'scheduled_time': '14:45:00',
                'proposed_date': self.proposed_date.isoformat(),
                'proposed_time': '14:45:00',
                'agent_notes': 'Proposed by the owner',
            },
            follow=True,
        )

        self.request_obj.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.request_obj.status, ViewingRequest.Status.PROPOSED)
        self.assertIsNone(self.request_obj.scheduled_date)
        self.assertEqual(self.request_obj.proposed_date, self.proposed_date)
        self.assertEqual(str(self.request_obj.proposed_time), '14:45:00')
        self.assertTrue(
            ViewingRequestEvent.objects.filter(
                viewing_request=self.request_obj,
                event_type=ViewingRequestEvent.Type.PROPOSAL_SENT,
            ).exists()
        )

        visitor_response = self.client.post(
            reverse('user_viewing_request_status'),
            {'receipt_token': self.receipt_token, 'decision': 'accept'},
        )
        self.request_obj.refresh_from_db()
        self.assertEqual(visitor_response.status_code, 200)
        self.assertEqual(self.request_obj.status, ViewingRequest.Status.CONFIRMED)
        self.assertEqual(self.request_obj.scheduled_date, self.proposed_date)
        self.assertEqual(str(self.request_obj.scheduled_time), '14:45:00')

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

    def test_legacy_public_pages_only_link_or_embed_opted_in_coordinates(self):
        self.property.latitude = Decimal('10.340000')
        self.property.longitude = Decimal('37.740000')
        self.property.save(update_fields=['latitude', 'longitude'])

        private_home = self.client.get(reverse('user_home'))
        private_listings = self.client.get(reverse('user_listings'))
        private_detail = self.client.get(
            reverse('user_property_detail', args=[self.property.slug])
        )
        self.assertContains(private_home, 'property-location-icon')
        self.assertContains(private_listings, 'property-location-icon')
        self.assertNotContains(private_home, 'openstreetmap.org/?mlat=')
        self.assertNotContains(private_listings, 'openstreetmap.org/?mlat=')
        self.assertNotContains(private_detail, 'export/embed.html')
        self.assertContains(private_detail, 'A precise map location has not been provided.')

        self.property.exact_location_is_public = True
        self.property.save(update_fields=['exact_location_is_public'])
        public_home = self.client.get(reverse('user_home'))
        public_listings = self.client.get(reverse('user_listings'))
        public_detail = self.client.get(
            reverse('user_property_detail', args=[self.property.slug])
        )

        self.assertContains(public_home, 'mlat=10.340000')
        self.assertContains(public_listings, 'mlon=37.740000')
        self.assertContains(public_detail, 'export/embed.html')
        self.assertContains(public_detail, '10.340000%2C37.740000')
        self.assertContains(public_home, 'Listed')
        self.assertContains(public_listings, 'Listed')
        self.assertContains(public_detail, 'Listed')
        self.assertContains(public_home, 'Available')
        self.assertContains(public_listings, 'Available')
        self.assertContains(public_detail, 'Available')

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
