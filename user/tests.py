from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from user.models import Property, ViewingRequest


class ViewingRequestApprovalTests(TestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_user(
            username='viewing-test-admin',
            password='SecurePass123!value',
            is_staff=True,
        )
        self.client.force_login(admin_user)
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
        )
        self.request_obj = ViewingRequest.objects.create(
            property=self.property,
            full_name='Test Buyer',
            email='buyer@example.com',
            phone='+251900000000',
            preferred_date='2026-10-12',
            preferred_time='10:30:00',
            message='I want to visit',
            status='pending',
        )

    def test_admin_can_approve_and_set_date_time(self):
        url = reverse('admin_viewing_update', args=[self.request_obj.pk])
        response = self.client.post(
            url,
            {
                'status': 'confirmed',
                'scheduled_date': '2026-10-14',
                'scheduled_time': '14:45:00',
                'notes': 'Confirmed by the agent',
            },
            follow=True,
        )

        self.request_obj.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.request_obj.status, 'confirmed')
        self.assertEqual(str(self.request_obj.scheduled_date), '2026-10-14')
        self.assertEqual(str(self.request_obj.scheduled_time), '14:45:00')
        self.assertIn('Confirmed', response.content.decode())

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
            is_featured=False,
        )

        response = self.client.get(reverse('user_home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, non_featured.title)
