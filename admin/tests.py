from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import DelegatedAccountInvitation, Profile
from admin.models import AdminAuditEvent, BrokerageSettings, HomepageNote, SocialMediaLink
from properties.models import ListingReport, Property, PropertyBrokerAssignment


User = get_user_model()


class AdminApiTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='platform-admin',
            password='SecurePass123!value',
            is_staff=True,
            is_superuser=True,
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

    def test_user_management_updates_ordinary_user_data_and_audits_without_exposing_pii(self):
        self.client.force_authenticate(user=self.admin_user)

        role_update = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.customer.pk}),
            {'role': Profile.Role.BROKER, 'broker_approved': True},
            format='json',
        )

        self.assertEqual(role_update.status_code, 400)
        contact_update = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.customer.pk}),
            {'email': 'updated-customer@example.com'},
            format='json',
        )
        self.assertEqual(contact_update.status_code, 200)
        self.assertEqual(contact_update.data['role'], Profile.Role.CUSTOMER)
        contact_event = AdminAuditEvent.objects.filter(
            action='user_updated',
            object_id=str(self.customer.pk),
        ).order_by('-pk').first()
        self.assertEqual(contact_event.changes['email'], 'updated')
        self.assertNotIn('updated-customer@example.com', str(contact_event.changes))

    def test_brokerage_contact_is_public_but_only_authorized_staff_can_update_it(self):
        public = self.client.get(reverse('api:brokerage-contact'))
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.data['business_name'], '')

        self.client.force_authenticate(user=self.customer)
        forbidden = self.client.patch(
            reverse('api:brokerage-contact'),
            {'phone': '+251900000000'},
            format='json',
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertFalse(BrokerageSettings.objects.exists())

        contact_manager = User.objects.create_user(
            username='brokerage-contact-manager',
            is_staff=True,
        )
        Profile.objects.create(
            user=contact_manager,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.SETTINGS_MANAGE],
        )
        self.client.force_authenticate(user=contact_manager)
        updated = self.client.patch(
            reverse('api:brokerage-contact'),
            {
                'business_name': 'Brokerage contact',
                'phone': '+251900000000',
                'email': 'contact@example.com',
            },
            format='json',
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['phone'], '+251900000000')
        settings_obj = BrokerageSettings.objects.get(pk=1)
        self.assertEqual(settings_obj.platform_owner, self.admin_user)
        audit = AdminAuditEvent.objects.get(action='brokerage_settings_updated')
        self.assertEqual(
            audit.changes['fields'],
            ['business_name', 'phone', 'email'],
        )
        self.assertNotIn('+251900000000', str(audit.changes))

    def test_legacy_admin_property_registration_publishes_available_listing(self):
        browser_client = Client()
        browser_client.force_login(self.admin_user)

        response = browser_client.post(
            reverse('admin_property_form'),
            {
                'title': 'Legacy admin published listing',
                'location': 'Verified area',
                'property_type': 'house',
                'listing_type': 'sale',
                'price': '250000',
                'bedrooms': 2,
                'bathrooms': 1,
                'area_sqft': 900,
                'description': 'Created by the protected administrator portal.',
                'status': Property.Status.AVAILABLE,
            },
        )

        self.assertEqual(response.status_code, 302)
        created = Property.objects.get(title='Legacy admin published listing')
        self.assertEqual(created.publication_status, Property.PublicationStatus.PUBLISHED)
        public_response = self.client.get(reverse('api:property-list'))
        self.assertIn(created.slug, [item['slug'] for item in public_response.data['results']])

    def test_homepage_notes_are_public_only_when_published_and_ordered(self):
        first = HomepageNote.objects.create(
            title='Second',
            text='second announcement',
            is_published=True,
            display_order=2,
        )
        HomepageNote.objects.create(
            title='Private',
            text='unpublished announcement',
            is_published=False,
            display_order=1,
        )
        last = HomepageNote.objects.create(
            title='First',
            text='first announcement',
            is_published=True,
            display_order=1,
        )

        response = self.client.get(reverse('api:homepage-note-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([note['id'] for note in response.data['results']], [last.pk, first.pk])
        self.assertNotIn('unpublished announcement', str(response.data))

    def test_homepage_note_management_requires_settings_permission_and_persists_changes(self):
        note_url = reverse('api:managed-homepage-note-list')
        payload = {
            'title': 'Welcome',
            'text': '<b>Plain text safely escaped by the client</b>',
            'is_published': True,
            'display_order': 4,
        }

        self.client.force_authenticate(user=self.customer)
        forbidden = self.client.post(note_url, payload, format='json')
        self.assertEqual(forbidden.status_code, 403)

        content_manager = User.objects.create_user(username='homepage-content-manager', is_staff=True)
        Profile.objects.create(
            user=content_manager,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.SETTINGS_MANAGE],
        )
        self.client.force_authenticate(user=content_manager)
        created = self.client.post(note_url, payload, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.get(reverse('api:homepage-note-list')).data['results'][0]['text'], payload['text'])

        updated = self.client.patch(
            reverse('api:managed-homepage-note-detail', kwargs={'pk': created.data['id']}),
            {'text': 'Updated welcome', 'display_order': 1},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['text'], 'Updated welcome')
        self.assertEqual(self.client.get(reverse('api:homepage-note-list')).data['results'][0]['text'], 'Updated welcome')

        deleted = self.client.delete(
            reverse('api:managed-homepage-note-detail', kwargs={'pk': created.data['id']}),
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(HomepageNote.objects.filter(pk=created.data['id']).exists())
        self.assertTrue(AdminAuditEvent.objects.filter(
            action='homepage_note_deleted',
            object_id=str(created.data['id']),
        ).exists())

    def test_social_links_require_authorization_and_only_enabled_https_links_are_public(self):
        contact_url = reverse('api:brokerage-contact')
        self.client.force_authenticate(user=self.customer)
        denied = self.client.patch(
            contact_url,
            {'social_links': [{'platform': 'facebook', 'url': 'https://facebook.com/example', 'is_enabled': True, 'display_order': 0}]},
            format='json',
        )
        self.assertEqual(denied.status_code, 403)

        content_manager = User.objects.create_user(username='social-link-manager', is_staff=True)
        Profile.objects.create(
            user=content_manager,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.SETTINGS_MANAGE],
        )
        self.client.force_authenticate(user=content_manager)
        updated = self.client.patch(
            contact_url,
            {
                'social_links': [
                    {'platform': 'facebook', 'url': 'https://facebook.com/example', 'is_enabled': True, 'display_order': 2},
                    {'platform': 'telegram', 'url': 'https://t.me/example', 'is_enabled': False, 'display_order': 1},
                ],
            },
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(SocialMediaLink.objects.count(), 2)
        self.client.force_authenticate(user=None)
        public = self.client.get(contact_url)
        self.assertEqual(
            public.data['social_links'],
            [{'platform': 'facebook', 'url': 'https://facebook.com/example', 'is_enabled': True, 'display_order': 2}],
        )
        self.assertNotIn('facebook_url', public.data)

        self.client.force_authenticate(user=content_manager)
        invalid = self.client.patch(
            contact_url,
            {'social_links': [{'platform': 'facebook', 'url': 'http://facebook.com/example', 'is_enabled': True, 'display_order': 0}]},
            format='json',
        )
        self.assertEqual(invalid.status_code, 400)

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

    def test_staff_flag_alone_does_not_grant_admin_api_access(self):
        delegated_without_permissions = User.objects.create_user(
            username='staff-without-permissions',
            password='SecurePass123!value',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated_without_permissions,
            role=Profile.Role.ADMINISTRATOR,
        )
        self.client.force_authenticate(user=delegated_without_permissions)

        response = self.client.get(reverse('api:admin-property-list'))

        self.assertEqual(response.status_code, 403)

    def test_owner_can_create_and_invite_delegated_administrator(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse('api:admin-delegated-account-list'),
            {
                'username': 'listing-reviewer',
                'email': 'reviewer@example.com',
                'role': Profile.Role.ADMINISTRATOR,
                'management_permissions': [
                    Profile.Permission.PROPERTY_VIEW_ALL,
                    Profile.Permission.PROPERTY_MODERATE,
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        account = User.objects.get(username='listing-reviewer')
        self.assertFalse(account.is_active)
        self.assertTrue(account.is_staff)
        self.assertFalse(account.is_superuser)
        self.assertEqual(
            account.profile.management_permissions,
            [Profile.Permission.PROPERTY_VIEW_ALL, Profile.Permission.PROPERTY_MODERATE],
        )
        token = response.data['invitation_token']
        self.assertEqual(len(token), 43)
        self.assertNotIn(token, str(AdminAuditEvent.objects.get(action='delegated_account_created').changes))
        self.assertTrue(
            DelegatedAccountInvitation.objects.filter(
                user=account,
                token_digest=DelegatedAccountInvitation.digest(token),
            ).exists()
        )

    def test_delegated_invitation_activates_user_once_with_password(self):
        self.client.force_authenticate(user=self.admin_user)
        created = self.client.post(
            reverse('api:admin-delegated-account-list'),
            {
                'username': 'invited-broker',
                'email': 'invited-broker@example.com',
                'role': Profile.Role.BROKER,
                'management_permissions': [
                    Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                    Profile.Permission.VIEWING_MANAGE_ASSIGNED,
                ],
            },
            format='json',
        )
        token = created.data['invitation_token']
        self.client.force_authenticate(user=None)

        accepted = self.client.post(
            reverse('api:invitation-accept'),
            {'token': token, 'password': 'Unique!InvitedAccount873'},
            format='json',
        )
        replay = self.client.post(
            reverse('api:invitation-accept'),
            {'token': token, 'password': 'Unique!InvitedAccount873'},
            format='json',
        )

        invited_user = User.objects.get(username='invited-broker')
        self.assertEqual(accepted.status_code, 200)
        self.assertTrue(invited_user.is_active)
        self.assertTrue(invited_user.check_password('Unique!InvitedAccount873'))
        self.assertEqual(invited_user.profile.role, Profile.Role.BROKER)
        self.assertEqual(replay.status_code, 400)

    def test_owner_can_assign_invited_broker_and_scope_access_to_that_listing(self):
        self.client.force_authenticate(user=self.admin_user)
        created = self.client.post(
            reverse('api:admin-delegated-account-list'),
            {
                'username': 'assigned-broker',
                'email': 'assigned-broker@example.com',
                'role': Profile.Role.BROKER,
                'management_permissions': [
                    Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                    Profile.Permission.VIEWING_MANAGE_ASSIGNED,
                ],
            },
            format='json',
        )
        broker = User.objects.get(username='assigned-broker')
        assignment = self.client.post(
            reverse(
                'api:admin-broker-assignment-list',
                kwargs={'property_id': self.property.pk},
            ),
            {'broker_id': broker.pk},
            format='json',
        )
        token = created.data['invitation_token']
        self.client.force_authenticate(user=None)
        accepted = self.client.post(
            reverse('api:invitation-accept'),
            {'token': token, 'password': 'Maple!RiverStone8294'},
            format='json',
        )

        self.assertEqual(assignment.status_code, 201)
        self.assertEqual(accepted.status_code, 200, accepted.data)
        broker.refresh_from_db()
        self.client.force_authenticate(user=broker)
        assigned_properties = self.client.get(reverse('api:managed-property-list'))
        self.assertEqual(assigned_properties.status_code, 200)
        self.assertEqual(assigned_properties.data['count'], 1)
        self.assertEqual(assigned_properties.data['results'][0]['id'], self.property.pk)

    def test_broker_cannot_receive_global_permissions_or_owner_only_permissions(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse('api:admin-delegated-account-list'),
            {
                'username': 'overprivileged-broker',
                'email': 'overprivileged@example.com',
                'role': Profile.Role.BROKER,
                'management_permissions': [Profile.Permission.PROPERTY_VIEW_ALL],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='overprivileged-broker').exists())

    def test_delegated_permissions_are_enforced_and_owner_can_revoke_them(self):
        delegated = User.objects.create_user(
            username='limited-reviewer',
            password='SecurePass123!value',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.PROPERTY_VIEW_ALL],
        )
        self.client.force_authenticate(user=delegated)

        can_view = self.client.get(reverse('api:admin-property-list'))
        cannot_moderate = self.client.patch(
            reverse('api:admin-property-detail', kwargs={'pk': self.property.pk}),
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )

        self.assertEqual(can_view.status_code, 200)
        self.assertEqual(cannot_moderate.status_code, 403)
        self.client.force_authenticate(user=self.admin_user)
        update_permissions = self.client.patch(
            reverse('api:admin-delegated-account-detail', kwargs={'pk': delegated.pk}),
            {
                'management_permissions': [
                    Profile.Permission.PROPERTY_VIEW_ALL,
                    Profile.Permission.PROPERTY_MODERATE,
                ],
            },
            format='json',
        )
        self.assertEqual(update_permissions.status_code, 200)
        self.assertTrue(
            AdminAuditEvent.objects.filter(action='delegated_account_updated').exists()
        )
        self.client.force_authenticate(user=delegated)
        can_moderate = self.client.patch(
            reverse('api:admin-property-detail', kwargs={'pk': self.property.pk}),
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )
        self.assertEqual(can_moderate.status_code, 200)

        self.client.force_authenticate(user=self.admin_user)
        revoked = self.client.patch(
            reverse('api:admin-delegated-account-detail', kwargs={'pk': delegated.pk}),
            {'management_permissions': []},
            format='json',
        )
        self.assertEqual(revoked.status_code, 200)
        self.client.force_authenticate(user=delegated)
        denied_after_revoke = self.client.get(reverse('api:admin-property-list'))
        self.assertEqual(denied_after_revoke.status_code, 403)

    def test_delegated_accounts_cannot_promote_themselves_or_change_owner_access(self):
        delegated = User.objects.create_user(
            username='no-self-promotion',
            password='SecurePass123!value',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.USERS_MANAGE],
        )
        self.client.force_authenticate(user=delegated)

        promotion = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': delegated.pk}),
            {'is_superuser': True, 'role': Profile.Role.OWNER},
            format='json',
        )
        protected_owner = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.admin_user.pk}),
            {'is_active': False, 'email': 'attacker@example.com'},
            format='json',
        )
        self.assertEqual(promotion.status_code, 404)
        self.assertEqual(protected_owner.status_code, 404)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)
        self.assertTrue(self.admin_user.is_superuser)

    def test_deactivated_delegated_administrator_loses_api_access(self):
        delegated = User.objects.create_user(
            username='deactivated-reviewer',
            password='SecurePass123!value',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.PROPERTY_VIEW_ALL],
        )
        self.client.force_authenticate(user=delegated)
        self.assertEqual(self.client.get(reverse('api:admin-property-list')).status_code, 200)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            reverse('api:admin-delegated-account-detail', kwargs={'pk': delegated.pk}),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        delegated.refresh_from_db()
        self.client.force_authenticate(user=delegated)
        self.assertEqual(self.client.get(reverse('api:admin-property-list')).status_code, 403)

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
        self.property.refresh_from_db()
        self.assertEqual(self.property.moderation_note, 'Listing details need correction.')
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='property_moderated',
                object_id=str(self.property.pk),
            ).exists()
        )
        self.client.force_authenticate(user=self.owner)
        owner_view = self.client.get(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk})
        )
        self.assertEqual(owner_view.status_code, 403)

    def test_admin_must_record_a_reason_when_suspending_a_listing(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('api:admin-property-detail', kwargs={'pk': self.property.pk})

        missing_reason = self.client.patch(
            url,
            {'publication_status': Property.PublicationStatus.SUSPENDED},
            format='json',
        )
        suspended = self.client.patch(
            url,
            {
                'publication_status': Property.PublicationStatus.SUSPENDED,
                'moderation_note': 'Temporarily suspended pending verification.',
            },
            format='json',
        )

        self.assertEqual(missing_reason.status_code, 400)
        self.assertEqual(suspended.status_code, 200)
        self.property.refresh_from_db()
        self.assertEqual(self.property.publication_status, Property.PublicationStatus.SUSPENDED)
        self.assertEqual(
            self.property.moderation_note,
            'Temporarily suspended pending verification.',
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
    def test_owner_can_create_delegated_account_invitation_from_portal(self):
        owner = User.objects.create_superuser(
            username='portal-owner',
            password='SecurePass123!value',
        )
        client = Client()
        client.force_login(owner)

        response = client.post(
            reverse('admin_delegated_accounts'),
            {
                'username': 'portal-broker',
                'email': 'portal-broker@example.com',
                'role': Profile.Role.BROKER,
                'management_permissions': [
                    Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                    Profile.Permission.VIEWING_MANAGE_ASSIGNED,
                ],
            },
        )

        invited = User.objects.get(username='portal-broker')
        invitation = DelegatedAccountInvitation.objects.get(user=invited)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Cache-Control', response)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertFalse(invited.is_active)
        self.assertEqual(invited.profile.role, Profile.Role.BROKER)
        self.assertEqual(invited.profile.management_permissions, [
            Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
            Profile.Permission.VIEWING_MANAGE_ASSIGNED,
        ])
        invitation_token = response.context['invitation_token']
        self.assertEqual(
            invitation.token_digest,
            DelegatedAccountInvitation.digest(invitation_token),
        )
        self.assertNotContains(response, invitation.token_digest)
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='delegated_account_created',
                object_id=str(invited.pk),
            ).exists()
        )

    def test_owner_portal_can_revoke_delegated_account_access(self):
        owner = User.objects.create_superuser(
            username='portal-access-owner',
            password='SecurePass123!value',
        )
        delegated = User.objects.create_user(
            username='portal-access-broker',
            password='SecurePass123!value',
            is_active=True,
        )
        profile = Profile.objects.create(
            user=delegated,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.PROPERTY_MANAGE_ASSIGNED],
        )
        client = Client()
        client.force_login(owner)

        response = client.post(
            reverse('admin_delegated_accounts'),
            {
                'account_id': str(delegated.pk),
                'role': Profile.Role.BROKER,
                'is_active': '',
                'management_permissions': [],
            },
        )

        self.assertEqual(response.status_code, 302)
        delegated.refresh_from_db()
        profile.refresh_from_db()
        self.assertFalse(delegated.is_active)
        self.assertEqual(profile.management_permissions, [])
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='delegated_account_updated',
                object_id=str(delegated.pk),
            ).exists()
        )

    def test_legacy_property_mutation_routes_require_post(self):
        staff = User.objects.create_superuser(
            username='legacy-portal-staff',
            password='SecurePass123!value',
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

    def test_staff_flag_alone_does_not_grant_legacy_portal_access(self):
        staff = User.objects.create_user(
            username='delegated-without-portal-permissions',
            password='SecurePass123!value',
            is_staff=True,
        )
        client = Client()
        client.force_login(staff)

        response = client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_staff_flag_alone_does_not_grant_django_admin_access(self):
        staff = User.objects.create_user(
            username='staff-without-django-admin-access',
            password='SecurePass123!value',
            is_staff=True,
        )
        client = Client()
        client.force_login(staff)

        response = client.get('/admin/')

        self.assertEqual(response.status_code, 403)

    def test_owner_post_to_toggle_route_changes_status_and_writes_audit(self):
        staff = User.objects.create_superuser(
            username='legacy-toggle-staff',
            password='SecurePass123!value',
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
