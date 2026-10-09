from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import Profile
from properties.models import Property, PropertyBrokerAssignment
from viewings.models import ViewingRequest


class PublicViewingRequestApiTests(APITestCase):
    def setUp(self):
        self.property = Property.objects.create(
            title='Viewing request house',
            slug='viewing-request-house-api',
            location='Submitted location',
            price=500000,
            description='A test listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

    def test_anonymous_visitor_can_submit_request_without_pii_in_response(self):
        response = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Test Visitor',
                'email': 'visitor@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
                'message': 'Please contact me.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'pending')
        self.assertNotIn('email', response.data)
        self.assertNotIn('phone', response.data)

    def test_past_date_returns_consistent_validation_error(self):
        response = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Test Visitor',
                'email': 'visitor@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() - timedelta(days=1)).isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['status_code'], 400)
        self.assertIn('preferred_date', response.data['error']['details'])

    def test_unavailable_property_cannot_receive_request(self):
        self.property.status = Property.Status.SOLD
        self.property.save()

        response = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Test Visitor',
                'email': 'visitor@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_viewing_request_endpoint_does_not_allow_public_reads(self):
        response = self.client.get(reverse('api:viewing-request-create'))

        self.assertEqual(response.status_code, 405)

    @patch.object(ScopedRateThrottle, 'get_rate', return_value='1/hour')
    def test_anonymous_submission_is_rate_limited(self, _get_rate):
        cache.clear()
        self.addCleanup(cache.clear)
        payload = {
            'property_id': self.property.pk,
            'full_name': 'Test Visitor',
            'email': 'visitor@example.com',
            'phone': '+251900000000',
            'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
        }

        first_response = self.client.post(
            reverse('api:viewing-request-create'),
            payload,
            format='json',
        )
        limited_response = self.client.post(
            reverse('api:viewing-request-create'),
            payload,
            format='json',
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(limited_response.status_code, 429)
        self.assertEqual(limited_response.data['error']['status_code'], 429)

    def test_authenticated_public_submission_is_linked_to_requester(self):
        user = get_user_model().objects.create_user(username='requester-customer')
        Profile.objects.create(user=user)
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Registered Visitor',
                'email': 'registered@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            ViewingRequest.objects.get(pk=response.data['id']).requester_id,
            user.pk,
        )


class ManagedViewingRequestApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username='viewing-owner')
        Profile.objects.create(user=self.owner, role=Profile.Role.OWNER)
        other_owner = user_model.objects.create_user(username='viewing-other-owner')
        Profile.objects.create(user=other_owner, role=Profile.Role.OWNER)
        self.broker = user_model.objects.create_user(username='viewing-approved-broker')
        Profile.objects.create(
            user=self.broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
        )
        self.unapproved_broker = user_model.objects.create_user(username='viewing-unapproved-broker')
        Profile.objects.create(
            user=self.unapproved_broker,
            role=Profile.Role.BROKER,
            broker_approved=False,
        )
        self.property = Property.objects.create(
            title='Managed viewing property',
            slug='managed-viewing-property',
            location='Submitted location',
            price=400000,
            description='A managed listing.',
            owner=self.owner,
        )
        self.other_property = Property.objects.create(
            title='Other viewing property',
            slug='other-viewing-property',
            location='Submitted location',
            price=300000,
            description='Another managed listing.',
            owner=other_owner,
        )
        PropertyBrokerAssignment.objects.create(property=self.property, broker=self.broker)
        PropertyBrokerAssignment.objects.create(property=self.property, broker=self.unapproved_broker)
        self.viewing = ViewingRequest.objects.create(
            property=self.property,
            full_name='Private Visitor',
            email='visitor@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=2),
            preferred_time='10:30',
        )
        self.other_viewing = ViewingRequest.objects.create(
            property=self.other_property,
            full_name='Other Visitor',
            email='other@example.com',
            phone='+251911111111',
            preferred_date=timezone.localdate() + timedelta(days=3),
        )

    def test_owner_sees_and_updates_only_requests_for_owned_listings(self):
        self.client.force_authenticate(user=self.owner)

        listed = self.client.get(reverse('api:managed-viewing-list'))
        updated = self.client.patch(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk}),
            {
                'status': 'confirmed',
                'agent_notes': 'Confirmed by the owner.',
                'email': 'attacker@example.com',
            },
            format='json',
        )
        hidden = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.other_viewing.pk})
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data['count'], 1)
        self.assertEqual(listed.data['results'][0]['email'], 'visitor@example.com')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['scheduled_date'], str(self.viewing.preferred_date))
        self.assertEqual(updated.data['email'], 'visitor@example.com')
        self.assertEqual(hidden.status_code, 404)

    def test_approved_assigned_broker_can_manage_but_unapproved_broker_cannot(self):
        self.client.force_authenticate(user=self.broker)
        allowed = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )

        self.assertEqual(allowed.status_code, 200)
        self.client.force_authenticate(user=self.unapproved_broker)
        denied = self.client.get(reverse('api:managed-viewing-list'))
        hidden = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(hidden.status_code, 403)
