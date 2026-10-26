import hashlib
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import Profile
from owner_announcements.models import InAppNotification
from properties.models import Location, Property, PropertyAgentAssignment
from viewings.models import ViewingRequest, ViewingRequestEvent
from viewings.notifications import notify_viewing_request_event


class PublicViewingRequestApiTests(APITestCase):
    def setUp(self):
        country = Location.objects.create(
            name='Viewing Test Country',
            slug='viewing-test-country',
            location_type=Location.Type.COUNTRY,
        )
        self.city = Location.objects.create(
            name='Viewing Test City',
            slug='viewing-test-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        self.subcity = Location.objects.create(
            name='Viewing Test Subcity',
            slug='viewing-test-subcity',
            location_type=Location.Type.SUBCITY,
            parent=self.city,
        )
        self.customer = get_user_model().objects.create_user(
            username='viewing-request-customer',
            email='customer@example.com',
        )
        Profile.objects.create(user=self.customer)
        self.client.force_authenticate(user=self.customer)
        self.property = Property.objects.create(
            title='Viewing request house',
            slug='viewing-request-house-api',
            location='Submitted location',
            administrative_location=self.subcity,
            price=500000,
            description='A test listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

    def test_anonymous_visitor_must_authenticate_before_submitting(self):
        self.client.force_authenticate(user=None)
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

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ViewingRequest.objects.exists())

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

    def test_missing_required_fields_are_rejected_without_creating_a_request(self):
        response = self.client.post(
            reverse('api:viewing-request-create'),
            {'property_id': self.property.pk},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        for field in ('full_name', 'email', 'phone', 'preferred_date'):
            self.assertIn(field, response.data['error']['details'])
        self.assertFalse(ViewingRequest.objects.exists())

    def test_past_preferred_time_today_is_rejected(self):
        past = timezone.localtime() - timedelta(minutes=5)
        response = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Test Visitor',
                'email': 'visitor@example.com',
                'phone': '+251900000000',
                'preferred_date': past.date().isoformat(),
                'preferred_time': past.time().replace(microsecond=0).isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('preferred_time', response.data['error']['details'])
        self.assertFalse(ViewingRequest.objects.exists())

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
    def test_authenticated_submission_is_rate_limited(self, _get_rate):
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
        self.assertNotIn('receipt_token', response.data)
        viewing = ViewingRequest.objects.get(pk=response.data['id'])
        self.assertEqual(
            viewing.requester_id,
            self.customer.pk,
        )

    def test_agent_cannot_submit_or_open_customer_viewing_requests(self):
        agent = get_user_model().objects.create_user(username='agent-cannot-request')
        Profile.objects.create(
            user=agent,
            role=Profile.Role.AGENT,
            agent_approved=True,
            assigned_city=self.city,
        )
        self.client.force_authenticate(user=agent)

        create_response = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Agent Account',
                'email': 'agent@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )
        list_response = self.client.get(reverse('api:customer-viewing-list'))

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(list_response.status_code, 403)
        self.assertFalse(ViewingRequest.objects.filter(requester=agent).exists())

    def test_different_customers_can_request_the_same_property_and_only_see_their_own(self):
        payload = {
            'property_id': self.property.pk,
            'full_name': 'First Customer',
            'email': 'first@example.com',
            'phone': '+251900000001',
            'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
        }
        first_response = self.client.post(
            reverse('api:viewing-request-create'),
            payload,
            format='json',
        )
        first_request_id = first_response.data['id']

        second_customer = get_user_model().objects.create_user(
            username='second-viewing-customer',
            email='second@example.com',
        )
        Profile.objects.create(user=second_customer, role=Profile.Role.CUSTOMER)
        self.client.force_authenticate(user=second_customer)
        second_response = self.client.post(
            reverse('api:viewing-request-create'),
            {
                **payload,
                'full_name': 'Second Customer',
                'email': 'second@example.com',
                'phone': '+251900000002',
            },
            format='json',
        )
        second_request_id = second_response.data['id']

        self.client.force_authenticate(user=self.customer)
        first_activity = self.client.get(reverse('api:activity'))
        self.client.force_authenticate(user=second_customer)
        second_activity = self.client.get(reverse('api:activity'))

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertNotEqual(first_request_id, second_request_id)
        self.assertEqual(
            [item['id'] for item in first_activity.data['viewing_requests']],
            [first_request_id],
        )
        self.assertEqual(
            [item['id'] for item in second_activity.data['viewing_requests']],
            [second_request_id],
        )

    def test_submitting_request_notifies_approved_agents(self):
        agent = get_user_model().objects.create_user(username='request-notification-agent')
        Profile.objects.create(
            user=agent,
            role=Profile.Role.AGENT,
            agent_approved=True,
            assigned_city=self.city,
        )
        PropertyAgentAssignment.objects.create(property=self.property, agent=agent)

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
        notification = InAppNotification.objects.get(recipient=agent)
        self.assertEqual(notification.notification_type, 'viewing_request_updated')
        self.assertIn(str(response.data['id']), notification.idempotency_key)
        event = ViewingRequestEvent.objects.get(viewing_request_id=response.data['id'])
        notify_viewing_request_event(
            event.viewing_request,
            event,
            to_requester=False,
        )
        self.assertEqual(InAppNotification.objects.filter(recipient=agent).count(), 1)

    def test_submitting_request_notifies_admin_who_published_property(self):
        admin = get_user_model().objects.create_user(
            username='published-property-admin',
            is_staff=True,
        )
        Profile.objects.create(
            user=admin,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.PROPERTY_EDIT_ALL],
        )
        property_obj = Property.objects.create(
            title='Admin published property',
            slug='admin-published-viewing-property',
            location='Submitted location',
            price=450000,
            description='A test listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
            submitted_by=admin,
        )

        response = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': property_obj.pk,
                'full_name': 'Registered Visitor',
                'email': 'registered@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            InAppNotification.objects.filter(
                recipient=admin,
                notification_type='viewing_request_updated',
            ).exists()
        )

    def test_active_duplicate_request_is_conflict_and_database_constraint_is_race_safe(self):
        payload = {
            'property_id': self.property.pk,
            'full_name': 'Registered Visitor',
            'email': 'registered@example.com',
            'phone': '+251900000000',
            'preferred_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
        }
        first = self.client.post(reverse('api:viewing-request-create'), payload, format='json')
        duplicate = self.client.post(reverse('api:viewing-request-create'), payload, format='json')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(ViewingRequest.objects.filter(requester=self.customer).count(), 1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ViewingRequest.objects.create(
                    requester=self.customer,
                    property=self.property,
                    full_name='Duplicate',
                    email='duplicate@example.com',
                    phone='+251900000000',
                    preferred_date=timezone.localdate() + timedelta(days=2),
                )

    def test_customer_can_submit_again_after_request_is_rejected(self):
        first = self.client.post(
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
        ViewingRequest.objects.filter(pk=first.data['id']).update(status=ViewingRequest.Status.REJECTED)

        retry = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Registered Visitor',
                'email': 'registered@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=2)).isoformat(),
            },
            format='json',
        )

        self.assertEqual(retry.status_code, 201)
        self.assertEqual(ViewingRequest.objects.filter(requester=self.customer).count(), 2)

    def test_customer_requests_are_paginated_private_and_cancel_keeps_history(self):
        request = ViewingRequest.objects.create(
            requester=self.customer,
            property=self.property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=2),
            preferred_time='10:30',
        )
        list_response = self.client.get(reverse('api:customer-viewing-list'))
        canceled = self.client.post(
            reverse('api:customer-viewing-cancel', kwargs={'pk': request.pk}),
            {'message': 'My plans changed.'},
            format='json',
        )
        request.refresh_from_db()

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(list_response.data['results'][0]['property']['id'], self.property.pk)
        self.assertEqual(canceled.status_code, 200)
        self.assertEqual(canceled.data['status'], ViewingRequest.Status.CANCELLED)
        self.assertEqual(request.events.count(), 1)
        self.assertEqual(request.events.get().message, 'My plans changed.')

    def test_requester_can_update_pending_request_and_managers_are_notified(self):
        admin = get_user_model().objects.create_user(
            username='viewing-request-update-admin',
            is_staff=True,
        )
        Profile.objects.create(
            user=admin,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.PROPERTY_EDIT_ALL],
        )
        self.property.submitted_by = admin
        self.property.save(update_fields=['submitted_by'])
        request = ViewingRequest.objects.create(
            requester=self.customer,
            property=self.property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=2),
        )
        preferred_date = (timezone.localdate() + timedelta(days=4)).isoformat()

        response = self.client.patch(
            reverse('api:customer-viewing-detail', kwargs={'pk': request.pk}),
            {
                'full_name': 'Updated Visitor',
                'preferred_date': preferred_date,
                'preferred_time': '14:30',
                'message': 'Please call before arriving.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        request.refresh_from_db()
        event = request.events.get()
        self.assertEqual(request.full_name, 'Updated Visitor')
        self.assertEqual(request.preferred_date.isoformat(), preferred_date)
        self.assertEqual(request.preferred_time.strftime('%H:%M'), '14:30')
        self.assertEqual(request.message, 'Please call before arriving.')
        self.assertEqual(event.event_type, ViewingRequestEvent.Type.REQUEST_UPDATED)
        self.assertEqual(event.proposed_date, request.preferred_date)
        self.assertEqual(event.proposed_time, request.preferred_time)
        self.assertTrue(
            InAppNotification.objects.filter(
                recipient=admin,
                notification_type='viewing_request_updated',
            ).exists()
        )

    def test_requester_cannot_update_after_a_manager_has_acted(self):
        request = ViewingRequest.objects.create(
            requester=self.customer,
            property=self.property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=2),
            status=ViewingRequest.Status.PROPOSED,
            proposed_date=timezone.localdate() + timedelta(days=3),
            proposed_time='10:30',
        )

        response = self.client.patch(
            reverse('api:customer-viewing-detail', kwargs={'pk': request.pk}),
            {'preferred_date': (timezone.localdate() + timedelta(days=4)).isoformat()},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        request.refresh_from_db()
        self.assertEqual(request.status, ViewingRequest.Status.PROPOSED)
        self.assertFalse(request.events.exists())

    def test_requester_can_hide_any_request_without_erasing_audit_history(self):
        request = ViewingRequest.objects.create(
            requester=self.customer,
            property=self.property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=2),
            status=ViewingRequest.Status.PENDING,
        )
        event = ViewingRequestEvent.objects.create(
            viewing_request=request,
            actor=self.customer,
            event_type=ViewingRequestEvent.Type.SUBMITTED,
            to_status=ViewingRequest.Status.PENDING,
        )

        response = self.client.delete(
            reverse('api:customer-viewing-detail', kwargs={'pk': request.pk}),
        )
        request.refresh_from_db()
        activity = self.client.get(reverse('api:customer-viewing-list'))

        self.assertEqual(response.status_code, 204)
        self.assertIsNotNone(request.requester_deleted_at)
        self.assertEqual(request.status, ViewingRequest.Status.CANCELLED)
        self.assertTrue(ViewingRequest.objects.filter(pk=request.pk).exists())
        self.assertTrue(ViewingRequestEvent.objects.filter(pk=event.pk).exists())
        self.assertTrue(
            ViewingRequestEvent.objects.filter(
                viewing_request=request,
                event_type=ViewingRequestEvent.Type.CANCELLED,
                actor=self.customer,
            ).exists()
        )
        self.assertEqual(activity.data['count'], 0)
        new_request = self.client.post(
            reverse('api:viewing-request-create'),
            {
                'property_id': self.property.pk,
                'full_name': 'Registered Visitor',
                'email': 'registered@example.com',
                'phone': '+251900000000',
                'preferred_date': (timezone.localdate() + timedelta(days=3)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(new_request.status_code, 201)

    def test_requester_cannot_hide_another_users_request(self):
        request = ViewingRequest.objects.create(
            requester=get_user_model().objects.create_user(username='another-viewing-requester'),
            property=self.property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=2),
            status=ViewingRequest.Status.PENDING,
        )

        response = self.client.delete(
            reverse('api:customer-viewing-detail', kwargs={'pk': request.pk}),
        )
        request.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(request.requester_deleted_at)
        self.assertEqual(request.status, ViewingRequest.Status.PENDING)

    def test_customer_request_list_supports_status_filter_ordering_and_pagination(self):
        earlier_property = Property.objects.create(
            title='Earlier viewing property',
            slug='earlier-viewing-property',
            location='Submitted location',
            price=450000,
            description='An earlier appointment request.',
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        later_property = Property.objects.create(
            title='Later viewing property',
            slug='later-viewing-property',
            location='Submitted location',
            price=550000,
            description='A later appointment request.',
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        earlier_request = ViewingRequest.objects.create(
            requester=self.customer,
            property=earlier_property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=2),
            status=ViewingRequest.Status.PENDING,
        )
        later_request = ViewingRequest.objects.create(
            requester=self.customer,
            property=later_property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=3),
            status=ViewingRequest.Status.PENDING,
        )
        ViewingRequest.objects.create(
            requester=self.customer,
            property=self.property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=1),
            status=ViewingRequest.Status.CANCELLED,
        )

        first_page = self.client.get(
            reverse('api:customer-viewing-list'),
            {'status': 'pending', 'ordering': 'preferred_date', 'page_size': 1},
        )
        second_page = self.client.get(
            reverse('api:customer-viewing-list'),
            {'status': 'pending', 'ordering': 'preferred_date', 'page_size': 1, 'page': 2},
        )

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data['count'], 2)
        self.assertIsNotNone(first_page.data['next'])
        self.assertEqual(first_page.data['results'][0]['id'], earlier_request.pk)
        self.assertEqual(second_page.data['results'][0]['id'], later_request.pk)
        self.assertEqual(second_page.data['results'][0]['status'], ViewingRequest.Status.PENDING)

    def test_customer_cannot_read_another_users_viewing_request(self):
        request = ViewingRequest.objects.create(
            requester=self.customer,
            property=self.property,
            full_name='Registered Visitor',
            email='registered@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=2),
        )
        other_customer = get_user_model().objects.create_user(username='other-viewing-customer')
        self.client.force_authenticate(user=other_customer)

        listed = self.client.get(reverse('api:customer-viewing-list'))
        detail = self.client.get(
            reverse('api:customer-viewing-detail', kwargs={'pk': request.pk})
        )
        respond = self.client.post(
            reverse('api:customer-viewing-response', kwargs={'pk': request.pk}),
            {'decision': 'accept'},
            format='json',
        )
        cancel = self.client.post(
            reverse('api:customer-viewing-cancel', kwargs={'pk': request.pk}),
            {'message': 'Not my request.'},
            format='json',
        )
        delete = self.client.delete(
            reverse('api:customer-viewing-detail', kwargs={'pk': request.pk}),
        )
        update = self.client.patch(
            reverse('api:customer-viewing-detail', kwargs={'pk': request.pk}),
            {'full_name': 'Unauthorized update'},
            format='json',
        )
        request.refresh_from_db()

        self.assertEqual(listed.data['count'], 0)
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(respond.status_code, 404)
        self.assertEqual(cancel.status_code, 404)
        self.assertEqual(delete.status_code, 404)
        self.assertEqual(update.status_code, 404)
        self.assertEqual(request.status, ViewingRequest.Status.PENDING)
        self.assertFalse(request.events.exists())

    def test_receipt_token_is_required_and_does_not_disclose_requester_details(self):
        receipt_token = 'legacy-guest-private-token'
        viewing = ViewingRequest.objects.create(
            property=self.property,
            full_name='Private Visitor',
            email='private@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=1),
            receipt_token_digest=hashlib.sha256(receipt_token.encode()).hexdigest(),
        )
        receipt_url = reverse('api:viewing-request-receipt')
        unauthorized = self.client.get(receipt_url)
        authorized = self.client.get(
            receipt_url,
            HTTP_X_VIEWING_RECEIPT=receipt_token,
        )

        self.assertEqual(unauthorized.status_code, 404)
        self.assertEqual(authorized.status_code, 200)
        self.assertEqual(authorized.data['id'], viewing.pk)
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
        manager = get_user_model().objects.create_user(username='proposal-agent')
        Profile.objects.create(
            user=manager,
            role=Profile.Role.AGENT,
            agent_approved=True,
            assigned_city=self.city,
            management_permissions=[Profile.Permission.VIEWING_MANAGE_ASSIGNED],
        )
        PropertyAgentAssignment.objects.create(property=request.property, agent=manager)
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

        self.client.force_authenticate(user=self.customer)
        customer_response = self.client.post(
            reverse('api:customer-viewing-response', kwargs={'pk': request.pk}),
            {'decision': 'accept'},
            format='json',
        )
        self.assertEqual(customer_response.status_code, 200)
        self.assertEqual(customer_response.data['status'], ViewingRequest.Status.CONFIRMED)
        self.assertEqual(
            customer_response.data['scheduled_date'],
            (timezone.localdate() + timedelta(days=2)).isoformat(),
        )
        request.refresh_from_db()
        self.assertEqual(
            request.events.order_by('-created_at', '-pk').first().event_type,
            'proposal_accepted',
        )
        self.assertTrue(InAppNotification.objects.filter(recipient=self.customer).exists())
        self.assertTrue(InAppNotification.objects.filter(recipient=manager).exists())

    def test_agent_can_revise_proposal_and_customer_sees_the_updated_schedule_and_history(self):
        agent = get_user_model().objects.create_user(username='revising-proposal-agent')
        Profile.objects.create(
            user=agent,
            role=Profile.Role.AGENT,
            agent_approved=True,
            assigned_city=self.city,
            management_permissions=[Profile.Permission.VIEWING_MANAGE_ASSIGNED],
        )
        PropertyAgentAssignment.objects.create(property=self.property, agent=agent)
        request = ViewingRequest.objects.create(
            property=self.property,
            requester=self.customer,
            full_name='Appointment Customer',
            email='appointment@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=1),
        )
        self.client.force_authenticate(user=agent)
        first_date = timezone.localdate() + timedelta(days=2)
        revised_date = timezone.localdate() + timedelta(days=3)

        first_proposal = self.client.patch(
            reverse('api:managed-viewing-detail', kwargs={'pk': request.pk}),
            {'proposed_date': first_date.isoformat(), 'proposed_time': '10:00'},
            format='json',
        )
        revised_proposal = self.client.patch(
            reverse('api:managed-viewing-detail', kwargs={'pk': request.pk}),
            {'proposed_date': revised_date.isoformat(), 'proposed_time': '11:30'},
            format='json',
        )
        self.client.force_authenticate(user=self.customer)
        customer_requests = self.client.get(reverse('api:customer-viewing-list'))

        self.assertEqual(first_proposal.status_code, 200)
        self.assertEqual(revised_proposal.status_code, 200)
        self.assertEqual(revised_proposal.data['status'], ViewingRequest.Status.PROPOSED)
        self.assertEqual(len(revised_proposal.data['events']), 2)
        self.assertEqual(revised_proposal.data['events'][-1]['event_type'], 'proposal_revised')
        self.assertEqual(customer_requests.status_code, 200)
        customer_request = customer_requests.data['results'][0]
        self.assertEqual(customer_request['proposed_date'], revised_date.isoformat())
        self.assertEqual(customer_request['proposed_time'], '11:30:00')
        self.assertEqual(customer_request['appointment_timezone'], 'Africa/Addis_Ababa')
        self.assertEqual(
            InAppNotification.objects.filter(
                recipient=self.customer,
                notification_type='viewing_request_updated',
            ).count(),
            2,
        )

    def test_customer_can_decline_a_proposal_and_agent_receives_notification(self):
        agent = get_user_model().objects.create_user(username='proposal-decline-agent')
        Profile.objects.create(
            user=agent,
            role=Profile.Role.AGENT,
            agent_approved=True,
            assigned_city=self.city,
            management_permissions=[Profile.Permission.VIEWING_MANAGE_ASSIGNED],
        )
        PropertyAgentAssignment.objects.create(property=self.property, agent=agent)
        customer = get_user_model().objects.create_user(username='declining-appointment-customer')
        Profile.objects.create(user=customer)
        request = ViewingRequest.objects.create(
            property=self.property,
            requester=customer,
            full_name='Declining Customer',
            email='declining@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=1),
            status=ViewingRequest.Status.PROPOSED,
            proposed_date=timezone.localdate() + timedelta(days=2),
            proposed_time='12:00',
        )
        self.client.force_authenticate(user=customer)

        declined = self.client.post(
            reverse('api:customer-viewing-response', kwargs={'pk': request.pk}),
            {'decision': 'decline'},
            format='json',
        )

        self.assertEqual(declined.status_code, 200)
        self.assertEqual(declined.data['status'], ViewingRequest.Status.DECLINED)
        request.refresh_from_db()
        self.assertEqual(
            request.events.latest('pk').event_type,
            ViewingRequestEvent.Type.PROPOSAL_DECLINED,
        )
        self.assertTrue(
            InAppNotification.objects.filter(
                recipient=agent,
                notification_type='viewing_request_updated',
            ).exists()
        )

    def test_guest_reference_number_is_not_sufficient_to_retrieve_request(self):
        guest = ViewingRequest.objects.create(
            property=self.property,
            full_name='Private Visitor',
            email='private@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=1),
        )

        response = self.client.get(
            f"{reverse('api:viewing-request-receipt')}?id={guest.pk}"
        )

        self.assertEqual(response.status_code, 404)


class ManagedViewingRequestApiTests(APITestCase):
    def setUp(self):
        country = Location.objects.create(
            name='Managed Viewing Country',
            slug='managed-viewing-country',
            location_type=Location.Type.COUNTRY,
        )
        self.city = Location.objects.create(
            name='Managed Viewing City',
            slug='managed-viewing-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        subcity = Location.objects.create(
            name='Managed Viewing Subcity',
            slug='managed-viewing-subcity',
            location_type=Location.Type.SUBCITY,
            parent=self.city,
        )
        other_city = Location.objects.create(
            name='Managed Viewing Other City',
            slug='managed-viewing-other-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        other_subcity = Location.objects.create(
            name='Managed Viewing Other Subcity',
            slug='managed-viewing-other-subcity',
            location_type=Location.Type.SUBCITY,
            parent=other_city,
        )
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username='viewing-owner')
        Profile.objects.create(user=self.owner, role=Profile.Role.OWNER)
        other_owner = user_model.objects.create_user(username='viewing-other-owner')
        Profile.objects.create(user=other_owner, role=Profile.Role.OWNER)
        self.agent = user_model.objects.create_user(username='viewing-approved-agent')
        Profile.objects.create(
            user=self.agent,
            role=Profile.Role.AGENT,
            agent_approved=True,
            assigned_city=self.city,
            management_permissions=[
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            ],
        )
        self.unapproved_agent = user_model.objects.create_user(username='viewing-unapproved-agent')
        Profile.objects.create(
            user=self.unapproved_agent,
            role=Profile.Role.AGENT,
            agent_approved=False,
            assigned_city=self.city,
        )
        self.property = Property.objects.create(
            title='Managed viewing property',
            slug='managed-viewing-property',
            location='Submitted location',
            administrative_location=subcity,
            price=400000,
            description='A managed listing.',
            owner=self.owner,
        )
        self.other_property = Property.objects.create(
            title='Other viewing property',
            slug='other-viewing-property',
            location='Submitted location',
            administrative_location=other_subcity,
            price=300000,
            description='Another managed listing.',
            owner=other_owner,
        )
        PropertyAgentAssignment.objects.create(property=self.property, agent=self.agent)
        PropertyAgentAssignment.objects.create(property=self.property, agent=self.unapproved_agent)
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

    def test_approved_agent_can_manage_requests_for_assigned_property(self):
        agent = get_user_model().objects.create_user(username='property-only-agent')
        Profile.objects.create(
            user=agent,
            role=Profile.Role.AGENT,
            agent_approved=True,
            assigned_city=self.city,
            management_permissions=[Profile.Permission.PROPERTY_MANAGE_ASSIGNED],
        )
        PropertyAgentAssignment.objects.create(property=self.property, agent=agent)
        self.client.force_authenticate(user=agent)

        detail = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )
        listed = self.client.get(reverse('api:managed-viewing-list'))

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(listed.status_code, 200)

    def test_approved_agent_cannot_view_requests_outside_a_specific_assignment(self):
        agent = get_user_model().objects.create_user(username='viewing-only-agent')
        Profile.objects.create(
            user=agent,
            role=Profile.Role.AGENT,
            agent_approved=True,
            assigned_city=self.city,
            management_permissions=[Profile.Permission.VIEWING_MANAGE_ASSIGNED],
        )
        PropertyAgentAssignment.objects.create(property=self.property, agent=agent)
        PropertyAgentAssignment.objects.create(property=self.other_property, agent=agent)
        self.client.force_authenticate(user=agent)

        response = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'visitor@example.com')
        visible = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.other_viewing.pk})
        )
        self.assertEqual(visible.status_code, 404)
        listed = self.client.get(reverse('api:managed-viewing-list'))
        self.assertEqual(listed.data['count'], 1)

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

    def test_administrator_can_manage_requests_for_a_property_they_published(self):
        admin = get_user_model().objects.create_user(
            username='viewing-property-admin',
            is_staff=True,
        )
        Profile.objects.create(
            user=admin,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.PROPERTY_EDIT_ALL],
        )
        property_obj = Property.objects.create(
            title='Administrator published listing',
            slug='administrator-published-listing',
            location='Submitted location',
            price=250000,
            description='A listing published by an administrator.',
            submitted_by=admin,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        viewing_request = ViewingRequest.objects.create(
            property=property_obj,
            full_name='Administrator Listing Visitor',
            email='visitor@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=3),
        )
        self.client.force_authenticate(user=admin)

        listed = self.client.get(reverse('api:managed-viewing-list'))
        detail = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': viewing_request.pk})
        )
        cancelled = self.client.post(
            reverse('api:managed-viewing-action', kwargs={'pk': viewing_request.pk}),
            {'action': 'cancel'},
            format='json',
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item['id'] for item in listed.data['results']], [viewing_request.pk])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(cancelled.status_code, 200)
        viewing_request.refresh_from_db()
        self.assertEqual(viewing_request.status, ViewingRequest.Status.CANCELLED)

    def test_approved_assigned_agent_can_manage_but_unapproved_agent_cannot(self):
        self.client.force_authenticate(user=self.agent)
        allowed = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )

        self.assertEqual(allowed.status_code, 200)
        self.client.force_authenticate(user=self.unapproved_agent)
        denied = self.client.get(reverse('api:managed-viewing-list'))
        hidden = self.client.get(
            reverse('api:managed-viewing-detail', kwargs={'pk': self.viewing.pk})
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(hidden.status_code, 403)

    def test_agent_can_confirm_requested_slot_and_customer_is_notified(self):
        customer = get_user_model().objects.create_user(username='appointment-customer')
        Profile.objects.create(user=customer)
        request = ViewingRequest.objects.create(
            property=self.property,
            requester=customer,
            full_name='Appointment Customer',
            email='appointment@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=3),
            preferred_time='11:30',
        )
        self.client.force_authenticate(user=self.agent)

        response = self.client.post(
            reverse('api:managed-viewing-action', kwargs={'pk': request.pk}),
            {'action': 'confirm_requested', 'message': 'We will meet at the entrance.'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ViewingRequest.Status.CONFIRMED)
        self.assertEqual(response.data['scheduled_time'], '11:30:00')
        self.assertTrue(InAppNotification.objects.filter(recipient=customer).exists())
        request.refresh_from_db()
        event = request.events.latest('pk')
        self.assertEqual(event.event_type, ViewingRequestEvent.Type.REQUEST_CONFIRMED)
        self.assertEqual(event.message, 'We will meet at the entrance.')

    def test_agent_cannot_complete_a_viewing_before_its_scheduled_time(self):
        request = ViewingRequest.objects.create(
            property=self.property,
            full_name='Completed Test Customer',
            email='completed@example.com',
            phone='+251900000000',
            preferred_date=timezone.localdate() + timedelta(days=3),
            status=ViewingRequest.Status.CONFIRMED,
            scheduled_date=timezone.localdate() + timedelta(days=2),
            scheduled_time='14:00',
        )
        self.client.force_authenticate(user=self.agent)

        early_response = self.client.post(
            reverse('api:managed-viewing-action', kwargs={'pk': request.pk}),
            {'action': 'complete'},
            format='json',
        )
        self.assertEqual(early_response.status_code, 409)

        request.scheduled_date = timezone.localdate() - timedelta(days=1)
        request.save(update_fields=['scheduled_date'])
        completed = self.client.post(
            reverse('api:managed-viewing-action', kwargs={'pk': request.pk}),
            {'action': 'complete'},
            format='json',
        )

        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.data['status'], ViewingRequest.Status.COMPLETED)
