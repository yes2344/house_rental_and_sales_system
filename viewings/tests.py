import hashlib
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
        self.assertTrue(response.data['receipt_token'])
        viewing = ViewingRequest.objects.get(pk=response.data['id'])
        self.assertEqual(
            viewing.receipt_token_digest,
            hashlib.sha256(response.data['receipt_token'].encode()).hexdigest(),
        )
        self.assertNotEqual(viewing.receipt_token_digest, response.data['receipt_token'])
        self.assertEqual(
            viewing.requester_id,
            user.pk,
        )

    def test_receipt_token_is_required_and_does_not_disclose_requester_details(self):
        created = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Private Visitor',
                'email': 'private@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )
        receipt_url = reverse('api:viewing-request-receipt')
        unauthorized = self.client.get(receipt_url)
        authorized = self.client.get(
            receipt_url,
            HTTP_X_VIEWING_RECEIPT=created.data['receipt_token'],
        )

        self.assertEqual(unauthorized.status_code, 404)
        self.assertEqual(authorized.status_code, 200)
        self.assertEqual(authorized.data['id'], created.data['id'])
        self.assertNotIn('email', authorized.data)
        self.assertNotIn('phone', authorized.data)
        self.assertNotIn('full_name', authorized.data)
        self.assertEqual(authorized['Cache-Control'], 'no-store')

    def test_visitor_must_accept_manager_proposal_before_confirmation(self):
        created = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Private Visitor',
                'email': 'private@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )
        request = ViewingRequest.objects.get(pk=created.data['id'])
        owner = get_user_model().objects.create_user(username='proposal-owner')
        Profile.objects.create(user=owner, role=Profile.Role.OWNER)
        manager = get_user_model().objects.create_user(username='proposal-broker')
        Profile.objects.create(
            user=manager,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.VIEWING_MANAGE_ASSIGNED],
        )
        PropertyBrokerAssignment.objects.create(property=request.property, broker=manager)
        request.property.owner = owner
        request.property.save(update_fields=['owner'])
        self.client.force_authenticate(user=manager)
        proposal = self.client.patch(
            reverse('api:managed-viewing-detail', kwargs={'pk': request.pk}),
            {
                'proposed_date': (timezone.localdate() + timedelta(days=2)).isoformat(),
                'proposed_time': '14:30',
                'status': 'confirmed',
            },
            format='json',
        )
        self.assertEqual(proposal.status_code, 400)

        direct_confirmation = self.client.patch(
            reverse('api:managed-viewing-detail', kwargs={'pk': request.pk}),
            {'status': 'confirmed'},
            format='json',
        )
        self.assertEqual(direct_confirmation.status_code, 400)

        proposal = self.client.patch(
            reverse('api:managed-viewing-detail', kwargs={'pk': request.pk}),
            {
                'proposed_date': (timezone.localdate() + timedelta(days=2)).isoformat(),
                'proposed_time': '14:30',
            },
            format='json',
        )
        self.assertEqual(proposal.status_code, 200)
        self.assertEqual(proposal.data['status'], ViewingRequest.Status.PROPOSED)
        self.assertIsNone(proposal.data['scheduled_date'])
        self.assertEqual(len(proposal.data['events']), 2)

        guest_response = self.client.post(
            reverse('api:viewing-request-receipt'),
            {'decision': 'accept'},
            format='json',
            HTTP_X_VIEWING_RECEIPT=created.data['receipt_token'],
        )
        self.assertEqual(guest_response.status_code, 200)
        self.assertEqual(guest_response.data['status'], ViewingRequest.Status.CONFIRMED)
        self.assertEqual(
            guest_response.data['scheduled_date'],
            (timezone.localdate() + timedelta(days=2)).isoformat(),
        )
        request.refresh_from_db()
        self.assertEqual(
            request.events.order_by('-created_at', '-pk').first().event_type,
            'proposal_accepted',
        )

    def test_guest_reference_number_is_not_sufficient_to_retrieve_request(self):
        created = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Private Visitor',
                'email': 'private@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )

        response = self.client.get(
            f"{reverse('api:viewing-request-receipt')}?id={created.data['id']}"
        )

        self.assertEqual(response.status_code, 404)


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
            management_permissions=[
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            ],
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
        self.customer = user_model.objects.create_user(username='viewing-submitter')
        self.submitted_property = Property.objects.create(
            title='Submitted viewing property',
            slug='submitted-viewing-property',
            location='Submitted location',
            price=350000,
            description='A property submitted by a registered user.',
            submitted_by=self.customer,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        self.submitted_viewing = ViewingRequest.objects.create(
            property=self.submitted_property,
            full_name='Submitted Property Visitor',
            email='submitted-visitor@example.com',
            phone='+251922222222',
            preferred_date=timezone.localdate() + timedelta(days=4),
        )

    def test_property_owner_cannot_manage_requests_from_ownership_alone(self):
        self.client.force_authenticate(user=self.owner)

        listed = self.client.get(reverse('api:managed-viewing-list'))
        denied_update = self.client.patch(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk}),
            {
                'proposed_date': (timezone.localdate() + timedelta(days=5)).isoformat(),
                'proposed_time': '15:00',
                'agent_notes': 'Unauthorized update.',
                'email': 'attacker@example.com',
            },
            format='json',
        )

        self.assertEqual(listed.status_code, 403)
        self.assertEqual(denied_update.status_code, 403)
        self.viewing.refresh_from_db()
        self.assertEqual(self.viewing.status, ViewingRequest.Status.PENDING)

    def test_assigned_property_permission_does_not_grant_viewing_request_access(self):
        broker = get_user_model().objects.create_user(username='property-only-broker')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.PROPERTY_MANAGE_ASSIGNED],
        )
        PropertyBrokerAssignment.objects.create(property=self.property, broker=broker)
        self.client.force_authenticate(user=broker)

        detail = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )
        listed = self.client.get(reverse('api:managed-viewing-list'))

        self.assertEqual(detail.status_code, 403)
        self.assertEqual(listed.status_code, 403)

    def test_viewing_permission_alone_scopes_assigned_broker_access(self):
        broker = get_user_model().objects.create_user(username='viewing-only-broker')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.VIEWING_MANAGE_ASSIGNED],
        )
        PropertyBrokerAssignment.objects.create(property=self.property, broker=broker)
        self.client.force_authenticate(user=broker)

        response = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'visitor@example.com')
        hidden = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.other_viewing.pk})
        )
        self.assertEqual(hidden.status_code, 404)

    def test_delegated_administrator_cannot_view_or_update_requests(self):
        delegated_admin = get_user_model().objects.create_user(
            username='viewing-reader',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated_admin,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.VIEWING_VIEW_ALL],
        )
        self.client.force_authenticate(user=delegated_admin)

        readable = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )
        forbidden = self.client.patch(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk}),
            {'agent_notes': 'unauthorized edit'},
            format='json',
        )

        self.assertEqual(readable.status_code, 403)
        self.assertEqual(forbidden.status_code, 403)

    def test_registered_submitter_cannot_manage_requests_for_their_own_property(self):
        self.client.force_authenticate(user=self.customer)

        listed = self.client.get(reverse('api:managed-viewing-list'))
        detail = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.submitted_viewing.pk})
        )

        self.assertEqual(listed.status_code, 403)
        self.assertEqual(detail.status_code, 403)

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
