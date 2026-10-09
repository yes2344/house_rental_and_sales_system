from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import Profile
from admin.models import AdminAuditEvent
from properties.models import ListingReport, Property, PropertyBrokerAssignment


User = get_user_model()


class AdminApiTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='platform-admin',
            password='SecurePass123!value',
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username='admin-managed-customer',
            password='SecurePass123!value',
            email='customer@example.com',
        )
        Profile.objects.create(user=self.customer, role=Profile.Role.CUSTOMER)
        self.owner = User.objects.create_user(
            username='admin-property-owner',
            password='SecurePass123!value',
        )
        Profile.objects.create(user=self.owner, role=Profile.Role.OWNER)
        self.property = Property.objects.create(
            title='Pending moderation listing',
            slug='pending-moderation-listing',
            location='Submitted location',
            listing_type=Property.ListingType.RENT,
            price=30000,
            description='Awaiting administrator review.',
            owner=self.owner,
        )

    def test_admin_user_management_updates_role_and_approval_with_audit(self):
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.customer.pk}),
            {'role': Profile.Role.BROKER, 'broker_approved': True},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], Profile.Role.BROKER)
        self.assertTrue(response.data['broker_approved'])
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='user_updated',
                object_id=str(self.customer.pk),
            ).exists()
        )
        contact_update = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.customer.pk}),
            {'email': 'updated-customer@example.com'},
            format='json',
        )
        self.assertEqual(contact_update.status_code, 200)
        contact_event = AdminAuditEvent.objects.filter(
            action='user_updated',
            object_id=str(self.customer.pk),
        ).order_by('-pk').first()
        self.assertEqual(contact_event.changes['email'], 'updated')
        self.assertNotIn('updated-customer@example.com', str(contact_event.changes))

    def test_user_management_cannot_grant_staff_privileges_or_self_deactivate(self):
        self.client.force_authenticate(user=self.admin_user)
        escalation = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.customer.pk}),
            {'is_staff': True, 'is_superuser': True},
            format='json',
        )
        self.assertEqual(escalation.status_code, 400)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_staff)
        self.assertFalse(self.customer.is_superuser)

        self_deactivation = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.admin_user.pk}),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(self_deactivation.status_code, 400)

    def test_admin_can_reject_a_listing_with_reason_and_audit(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('api:admin-property-detail', kwargs={'pk': self.property.pk})

        missing_reason = self.client.patch(
            url,
            {'publication_status': Property.PublicationStatus.REJECTED},
            format='json',
        )
        rejected = self.client.patch(
            url,
            {
                'publication_status': Property.PublicationStatus.REJECTED,
                'moderation_note': 'Listing details need correction.',
            },
            format='json',
        )

        self.assertEqual(missing_reason.status_code, 400)
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.data['publication_status'], Property.PublicationStatus.REJECTED)
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='property_moderated',
                object_id=str(self.property.pk),
            ).exists()
        )

    def test_admin_cannot_publish_a_sold_or_rented_listing(self):
        self.property.status = Property.Status.RENTED
        self.property.save()
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(
            reverse('api:admin-property-detail', kwargs={'pk': self.property.pk}),
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_public_report_submission_hides_reporter_data_and_admin_can_review(self):
        self.property.publication_status = Property.PublicationStatus.PUBLISHED
        self.property.status = Property.Status.AVAILABLE
        self.property.save()
        submitted = self.client.post(
            reverse('api:listing-report-create'),
            {
                'property_id': self.property.pk,
                'reporter_name': 'Concerned Visitor',
                'reporter_email': 'visitor@example.com',
                'reason': ListingReport.Reason.INACCURATE,
                'details': 'The stated room count looks incorrect.',
            },
            format='json',
        )

        self.assertEqual(submitted.status_code, 201)
        self.assertNotIn('reporter_email', submitted.data)
        report = ListingReport.objects.get(pk=submitted.data['id'])
        self.client.force_authenticate(user=self.admin_user)
        reviewed = self.client.patch(
            reverse('api:admin-report-detail', kwargs={'pk': report.pk}),
            {
                'status': ListingReport.Status.ACTION_TAKEN,
                'moderator_notes': 'Owner contacted to verify details.',
            },
            format='json',
        )

        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.data['reviewed_by'], self.admin_user.pk)
        self.assertIsNotNone(reviewed.data['reviewed_at'])
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='report_reviewed',
                object_id=str(report.pk),
            ).exists()
        )

    def test_only_staff_can_access_admin_api_or_legacy_admin_portal(self):
        self.client.force_authenticate(user=self.customer)
        api_response = self.client.get(reverse('api:admin-user-list'))
        self.assertEqual(api_response.status_code, 403)

        self.client.force_authenticate(user=None)
        portal_response = self.client.get('/admin-portal/')
        self.assertEqual(portal_response.status_code, 302)

    def test_admin_can_assign_only_approved_brokers_and_audit_assignment(self):
        broker = User.objects.create_user(
            username='approved-assignee',
            password='SecurePass123!value',
        )
        unapproved_broker = User.objects.create_user(
            username='unapproved-assignee',
            password='SecurePass123!value',
        )
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
        )
        Profile.objects.create(
            user=unapproved_broker,
            role=Profile.Role.BROKER,
            broker_approved=False,
        )
        self.client.force_authenticate(user=self.admin_user)

        denied = self.client.post(
            reverse(
                'api:admin-broker-assignment-list',
                kwargs={'property_id': self.property.pk},
            ),
            {'broker_id': unapproved_broker.pk},
            format='json',
        )
        assigned = self.client.post(
            reverse(
                'api:admin-broker-assignment-list',
                kwargs={'property_id': self.property.pk},
            ),
            {'broker_id': broker.pk},
            format='json',
        )

        self.assertEqual(denied.status_code, 400)
        self.assertEqual(assigned.status_code, 201)
        self.assertEqual(assigned.data['broker_id'], broker.pk)
        self.assertTrue(
            PropertyBrokerAssignment.objects.filter(
                property=self.property,
                broker=broker,
                granted_by=self.admin_user,
            ).exists()
        )
        self.assertTrue(
            AdminAuditEvent.objects.filter(action='broker_assigned').exists()
        )

        removed = self.client.delete(
            reverse(
                'api:admin-broker-assignment-detail',
                kwargs={'property_id': self.property.pk, 'broker_id': broker.pk},
            )
        )
        self.assertEqual(removed.status_code, 204)
        self.assertTrue(AdminAuditEvent.objects.filter(action='broker_unassigned').exists())


class AdminPortalMethodTests(TestCase):
    def test_legacy_property_mutation_routes_require_post(self):
        staff = User.objects.create_user(
            username='legacy-portal-staff',
            password='SecurePass123!value',
            is_staff=True,
        )
        property_obj = Property.objects.create(
            title='Legacy portal property',
            slug='legacy-portal-property',
            location='Submitted location',
            price=100000,
            description='Legacy management test.',
            status=Property.Status.AVAILABLE,
        )
        client = Client()
        client.force_login(staff)

        response = client.get(
            reverse('admin_property_toggle', kwargs={'pk': property_obj.pk})
        )

        self.assertEqual(response.status_code, 405)
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, Property.Status.AVAILABLE)

    def test_staff_post_to_toggle_route_changes_status_and_writes_audit(self):
        staff = User.objects.create_user(
            username='legacy-toggle-staff',
            password='SecurePass123!value',
            is_staff=True,
        )
        property_obj = Property.objects.create(
            title='Toggle portal property',
            slug='toggle-portal-property',
            location='Submitted location',
            price=100000,
            description='Legacy toggle test.',
            status=Property.Status.AVAILABLE,
        )
        client = Client()
        client.force_login(staff)

        response = client.post(reverse('admin_property_toggle', kwargs={'pk': property_obj.pk}))

        self.assertEqual(response.status_code, 302)
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, Property.Status.INACTIVE)
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='property_status_changed',
                object_id=str(property_obj.pk),
            ).exists()
        )
