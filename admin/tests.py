import re
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import DelegatedAccountInvitation, Profile
from admin.models import AdminAuditEvent, BrokerageSettings, HomepageNote, SocialMediaLink
from properties.models import ListingReport, Property, PropertyBrokerAssignment


User = get_user_model()


class AdminApiTests(APITestCase):
    def create_broker(self, username):
        broker = User.objects.create_user(username=username, email=f'{username}@example.com')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
        )
        return broker

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

    def test_django_superuser_can_manage_brokers_and_marketplace_operations(self):
        broker = User.objects.create_user(
            username='django-admin-managed-broker',
            email='managed-broker@example.com',
        )
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
        )
        delegated_admin = User.objects.create_user(
            username='another-delegated-admin',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated_admin,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.USERS_MANAGE],
        )
        self.client.force_authenticate(user=self.admin_user)

        me = self.client.get(reverse('api:me'))
        broker_accounts = self.client.get(reverse('api:admin-delegated-account-list'))
        users = self.client.get(reverse('api:admin-user-list'))
        listings = self.client.get(reverse('api:managed-property-list'))
        legacy_dashboard = self.client.get('/admin-portal/')
        legacy_properties = self.client.get('/admin-portal/properties/')

        self.assertEqual(me.data['role'], Profile.Role.ADMINISTRATOR)
        self.assertEqual(me.data['management_permissions'], list(Profile.Permission.values))
        self.assertEqual([account['id'] for account in broker_accounts.data['results']], [broker.pk])
        self.assertEqual([account['id'] for account in users.data['results']], [broker.pk])
        self.assertEqual(listings.status_code, 200)
        self.assertEqual(
            self.client.get(reverse('api:managed-location-list')).status_code,
            200,
        )
        self.assertEqual(legacy_dashboard.status_code, 302)
        self.assertEqual(legacy_dashboard.url, '/admin/login/')
        self.assertEqual(legacy_properties.status_code, 302)
        self.assertEqual(legacy_properties.url, '/admin/login/')

    def test_application_user_management_is_limited_to_brokers(self):
        broker = self.create_broker('managed-contact-broker')
        self.client.force_authenticate(user=self.admin_user)

        customer_update = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.customer.pk}),
            {'email': 'updated-customer@example.com'},
            format='json',
        )
        broker_update = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': broker.pk}),
            {'email': 'updated-broker@example.com'},
            format='json',
        )
        self.assertEqual(customer_update.status_code, 404)
        self.assertEqual(broker_update.status_code, 200)
        self.assertEqual(broker_update.data['role'], Profile.Role.BROKER)
        contact_event = AdminAuditEvent.objects.filter(
            action='user_updated',
            object_id=str(broker.pk),
        ).order_by('-pk').first()
        self.assertEqual(contact_event.changes['email'], 'updated')
        self.assertNotIn('updated-broker@example.com', str(contact_event.changes))

    def test_brokerage_contact_is_public_but_only_brokers_and_superusers_can_update_it(self):
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
            management_permissions=[Profile.Permission.USERS_MANAGE, Profile.Permission.SETTINGS_MANAGE],
        )
        self.client.force_authenticate(user=contact_manager)
        denied_update = self.client.patch(
            reverse('api:brokerage-contact'),
            {
                'business_name': 'Brokerage contact',
                'phone': '+251900000000',
                'email': 'contact@example.com',
            },
            format='json',
        )
        self.assertEqual(denied_update.status_code, 403)
        self.assertFalse(BrokerageSettings.objects.exists())

        self.client.force_authenticate(user=self.admin_user)
        superuser_update = self.client.patch(
            reverse('api:brokerage-contact'),
            {
                'business_name': 'Brokerage contact',
                'phone': '+251900000000',
                'email': 'contact@example.com',
            },
            format='json',
        )
        self.assertEqual(superuser_update.status_code, 200)
        contact_manager = self.create_broker('brokerage-contact-broker')
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
        audits = AdminAuditEvent.objects.filter(action='brokerage_settings_updated')
        self.assertEqual(audits.count(), 2)
        for audit in audits:
            self.assertEqual(
                audit.changes['fields'],
                ['business_name', 'phone', 'email'],
            )
            self.assertNotIn('+251900000000', str(audit.changes))

    def test_superuser_cannot_create_marketplace_listings_in_legacy_portal(self):
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
        self.assertEqual(response.url, '/admin-portal/delegated-accounts/')
        self.assertFalse(Property.objects.filter(title='Legacy admin published listing').exists())

    def test_superuser_cannot_upload_marketplace_listing_images_in_legacy_portal(self):
        browser_client = Client()
        browser_client.force_login(self.admin_user)
        media_directory = self.enterContext(TemporaryDirectory())

        with override_settings(MEDIA_ROOT=media_directory):
            response = browser_client.post(
                reverse('admin_property_form'),
                {
                    'title': 'Legacy admin listing with photos',
                    'location': 'Verified area',
                    'property_type': 'house',
                    'listing_type': 'sale',
                    'price': '250000',
                    'bedrooms': 2,
                    'bathrooms': 1,
                    'area_sqft': 900,
                    'description': 'Created with multiple uploaded photos.',
                    'status': Property.Status.AVAILABLE,
                    'images': [
                        SimpleUploadedFile('front.jpg', b'front-photo', content_type='image/jpeg'),
                        SimpleUploadedFile('inside.png', b'inside-photo', content_type='image/png'),
                    ],
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin-portal/delegated-accounts/')
        self.assertFalse(Property.objects.filter(title='Legacy admin listing with photos').exists())

    def test_superuser_cannot_create_marketplace_listing_with_coordinates_in_legacy_portal(self):
        browser_client = Client()
        browser_client.force_login(self.admin_user)
        form_page = browser_client.get(reverse('admin_property_form'))
        self.assertEqual(form_page.status_code, 302)
        self.assertEqual(form_page.url, '/admin-portal/delegated-accounts/')

        response = browser_client.post(
            reverse('admin_property_form'),
            {
                'title': 'Admin map listing',
                'location': 'Verified area',
                'latitude': '9.035812',
                'longitude': '38.752432',
                'exact_location_is_public': 'on',
                'property_type': 'house',
                'listing_type': 'sale',
                'price': '250000',
                'bedrooms': 2,
                'bathrooms': 1,
                'area_sqft': 900,
                'description': 'A listing with an explicitly selected location.',
                'status': Property.Status.AVAILABLE,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin-portal/delegated-accounts/')
        self.assertFalse(Property.objects.filter(title='Admin map listing').exists())

    def test_superuser_cannot_submit_partial_coordinates_in_legacy_portal(self):
        browser_client = Client()
        browser_client.force_login(self.admin_user)

        response = browser_client.post(
            reverse('admin_property_form'),
            {
                'title': 'Admin partial map listing',
                'location': 'Verified area',
                'latitude': '9.035812',
                'longitude': '',
                'property_type': 'house',
                'listing_type': 'sale',
                'price': '250000',
                'bedrooms': 2,
                'bathrooms': 1,
                'area_sqft': 900,
                'description': 'A listing with incomplete coordinates.',
                'status': Property.Status.AVAILABLE,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin-portal/delegated-accounts/')
        self.assertFalse(Property.objects.filter(title='Admin partial map listing').exists())

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

    def test_homepage_note_management_is_broker_only_and_persists_changes(self):
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
            management_permissions=[Profile.Permission.USERS_MANAGE, Profile.Permission.SETTINGS_MANAGE],
        )
        self.client.force_authenticate(user=content_manager)
        denied = self.client.post(note_url, payload, format='json')
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(user=self.create_broker('homepage-note-broker'))
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

    def test_approved_broker_can_manage_brokerage_contact_and_published_homepage_announcements(self):
        broker = User.objects.create_user(username='approved-broker-content-manager')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
        )
        self.client.force_authenticate(user=broker)

        contact = self.client.patch(
            reverse('api:brokerage-contact'),
            {
                'business_name': 'Broker-managed Realty',
                'phone': '+251900000001',
                'email': 'broker@example.com',
                'social_links': [
                    {
                        'platform': 'whatsapp',
                        'url': 'https://wa.me/251900000001',
                        'is_enabled': True,
                        'display_order': 0,
                    },
                ],
            },
            format='json',
        )
        announcement = self.client.post(
            reverse('api:managed-homepage-note-list'),
            {
                'title': 'Broker announcement',
                'text': 'A message written by the authorized broker.',
                'is_published': True,
                'display_order': 0,
            },
            format='json',
        )

        self.assertEqual(contact.status_code, 200)
        self.assertEqual(announcement.status_code, 201)
        self.client.force_authenticate(user=None)
        public_contact = self.client.get(reverse('api:brokerage-contact'))
        public_announcements = self.client.get(reverse('api:homepage-note-list'))
        self.assertEqual(public_contact.data['phone'], '+251900000001')
        self.assertEqual(public_contact.data['social_links'][0]['url'], 'https://wa.me/251900000001')
        self.assertEqual(
            [note['text'] for note in public_announcements.data['results']],
            ['A message written by the authorized broker.'],
        )

    def test_social_links_are_broker_managed_and_only_enabled_https_links_are_public(self):
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
            management_permissions=[Profile.Permission.USERS_MANAGE, Profile.Permission.SETTINGS_MANAGE],
        )
        self.client.force_authenticate(user=content_manager)
        denied = self.client.patch(
            contact_url,
            {
                'social_links': [
                    {'platform': 'facebook', 'url': 'https://facebook.com/example', 'is_enabled': True, 'display_order': 2},
                    {'platform': 'telegram', 'url': 'https://t.me/example', 'is_enabled': False, 'display_order': 1},
                ],
            },
            format='json',
        )
        self.assertEqual(denied.status_code, 403)
        social_broker = self.create_broker('social-link-broker')
        self.client.force_authenticate(user=social_broker)
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

        self.client.force_authenticate(user=social_broker)
        invalid = self.client.patch(
            contact_url,
            {'social_links': [{'platform': 'facebook', 'url': 'http://facebook.com/example', 'is_enabled': True, 'display_order': 0}]},
            format='json',
        )
        self.assertEqual(invalid.status_code, 400)

    def test_application_user_management_cannot_access_non_broker_or_admin_accounts(self):
        self.client.force_authenticate(user=self.admin_user)
        escalation = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.customer.pk}),
            {'is_staff': True, 'is_superuser': True},
            format='json',
        )
        self.assertEqual(escalation.status_code, 404)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_staff)
        self.assertFalse(self.customer.is_superuser)

        self_deactivation = self.client.patch(
            reverse('api:admin-user-detail', kwargs={'pk': self.admin_user.pk}),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(self_deactivation.status_code, 404)

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

    def test_superuser_cannot_create_delegated_administrators_in_the_application(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse('api:admin-delegated-account-list'),
            {
                'username': 'listing-reviewer',
                'email': 'reviewer@example.com',
                'role': Profile.Role.ADMINISTRATOR,
                'management_permissions': [Profile.Permission.USERS_MANAGE],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='listing-reviewer').exists())
        browser_client = Client()
        browser_client.force_login(self.admin_user)
        self.assertEqual(browser_client.get('/admin/auth/user/add/').status_code, 200)

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

    def test_superuser_can_invite_and_assign_a_broker_from_the_application(self):
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
        self.assertEqual(
            set(broker.profile.management_permissions),
            {
                permission
                for permission, _ in Profile.Permission.choices
                if permission not in {
                    Profile.Permission.USERS_MANAGE,
                    Profile.Permission.STAFF_MANAGE,
                }
            },
        )

    def test_broker_invitation_grants_all_marketplace_permissions_but_not_account_control(self):
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

        self.assertEqual(response.status_code, 201)
        broker = User.objects.get(username='overprivileged-broker')
        self.assertEqual(
            set(broker.profile.management_permissions),
            {
                permission
                for permission, _ in Profile.Permission.choices
                if permission not in {
                    Profile.Permission.USERS_MANAGE,
                    Profile.Permission.STAFF_MANAGE,
                }
            },
        )
        self.assertEqual(
            self.client.post(
                reverse('api:admin-delegated-account-list'),
                {
                    'username': 'owner-control-broker',
                    'email': 'owner-control@example.com',
                    'role': Profile.Role.BROKER,
                    'management_permissions': [Profile.Permission.STAFF_MANAGE],
                },
                format='json',
            ).status_code,
            400,
        )

    def test_delegated_administrators_cannot_manage_listings_even_if_legacy_permissions_exist(self):
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

        self.assertEqual(can_view.status_code, 403)
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
        self.assertEqual(update_permissions.status_code, 404)
        update_permissions = self.client.patch(
            reverse('api:admin-delegated-account-detail', kwargs={'pk': delegated.pk}),
            {'management_permissions': [Profile.Permission.USERS_MANAGE]},
            format='json',
        )
        self.assertEqual(update_permissions.status_code, 404)
        self.assertFalse(
            AdminAuditEvent.objects.filter(action='delegated_account_updated').exists()
        )
        delegated.profile.refresh_from_db()
        self.assertEqual(
            delegated.profile.management_permissions,
            [Profile.Permission.PROPERTY_VIEW_ALL],
        )
        self.client.force_authenticate(user=delegated)
        can_moderate = self.client.patch(
            reverse('api:admin-property-detail', kwargs={'pk': self.property.pk}),
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )
        self.assertEqual(can_moderate.status_code, 403)

        self.client.force_authenticate(user=self.admin_user)
        revoked = self.client.patch(
            reverse('api:admin-delegated-account-detail', kwargs={'pk': delegated.pk}),
            {'management_permissions': []},
            format='json',
        )
        self.assertEqual(revoked.status_code, 404)
        self.client.force_authenticate(user=delegated)
        denied_after_permission_update = self.client.get(reverse('api:admin-property-list'))
        self.assertEqual(denied_after_permission_update.status_code, 403)

    def test_delegated_administrator_can_manage_only_broker_accounts(self):
        delegated_admin = User.objects.create_user(
            username='broker-account-admin',
            password='SecurePass123!value',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated_admin,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[
                Profile.Permission.PROPERTY_VIEW_ALL,
                Profile.Permission.VIEWING_VIEW_ALL,
                Profile.Permission.SETTINGS_MANAGE,
            ],
        )
        broker = User.objects.create_user(
            username='managed-by-delegated-admin',
            email='managed-broker@example.com',
        )
        Profile.objects.create(user=broker, role=Profile.Role.BROKER, broker_approved=True)
        self.client.force_authenticate(user=delegated_admin)

        current_account = self.client.get(reverse('api:me'))
        users = self.client.get(reverse('api:admin-user-list'))
        delegated_accounts = self.client.get(reverse('api:admin-delegated-account-list'))
        created = self.client.post(
            reverse('api:admin-delegated-account-list'),
            {
                'username': 'new-delegated-broker',
                'email': 'new-delegated-broker@example.com',
                'role': Profile.Role.BROKER,
            },
            format='json',
        )
        cannot_create_admin = self.client.post(
            reverse('api:admin-delegated-account-list'),
            {
                'username': 'new-delegated-admin',
                'email': 'new-delegated-admin@example.com',
                'role': Profile.Role.ADMINISTRATOR,
            },
            format='json',
        )
        self.assertEqual(current_account.status_code, 200)
        self.assertEqual(current_account.data['management_permissions'], [Profile.Permission.USERS_MANAGE])
        self.assertEqual(users.status_code, 200)
        self.assertEqual([row['id'] for row in users.data['results']], [broker.pk])
        self.assertEqual(delegated_accounts.status_code, 200)
        self.assertEqual([row['id'] for row in delegated_accounts.data['results']], [broker.pk])
        self.assertEqual(created.status_code, 201)
        created_broker = User.objects.get(username='new-delegated-broker')
        self.assertEqual(
            set(created_broker.profile.management_permissions),
            {
                permission
                for permission, _ in Profile.Permission.choices
                if permission not in {
                    Profile.Permission.USERS_MANAGE,
                    Profile.Permission.STAFF_MANAGE,
                }
            },
        )
        self.assertEqual(cannot_create_admin.status_code, 400)

        self.assertEqual(self.client.get(reverse('api:managed-property-list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('api:managed-viewing-list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('api:admin-property-list')).status_code, 403)
        self.assertEqual(
            self.client.patch(
                reverse('api:brokerage-contact'),
                {'phone': '+251900000000'},
                format='json',
            ).status_code,
            403,
        )

    def test_delegated_administrator_portal_shows_only_broker_account_management(self):
        delegated_admin = User.objects.create_user(
            username='broker-portal-admin',
            password='SecurePass123!value',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated_admin,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.USERS_MANAGE],
        )
        client = Client()
        client.force_login(delegated_admin)

        response = client.get(reverse('admin_delegated_accounts'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invite a broker')
        self.assertNotContains(response, '/admin-portal/properties/')
        self.assertNotContains(response, '/admin-portal/viewing-requests/')
        self.assertEqual(client.get(reverse('admin_property_list')).status_code, 302)

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

    def test_superuser_can_deactivate_a_broker_but_not_a_delegated_administrator(self):
        delegated = User.objects.create_user(
            username='deactivated-reviewer',
            password='SecurePass123!value',
            is_staff=True,
        )
        Profile.objects.create(
            user=delegated,
            role=Profile.Role.ADMINISTRATOR,
            management_permissions=[Profile.Permission.USERS_MANAGE],
        )
        broker = self.create_broker('deactivated-broker')
        self.client.force_authenticate(user=delegated)
        self.assertEqual(
            self.client.get(reverse('api:admin-delegated-account-list')).status_code,
            200,
        )

        self.client.force_authenticate(user=self.admin_user)
        cannot_deactivate_admin = self.client.patch(
            reverse('api:admin-delegated-account-detail', kwargs={'pk': delegated.pk}),
            {'is_active': False},
            format='json',
        )
        response = self.client.patch(
            reverse('api:admin-delegated-account-detail', kwargs={'pk': broker.pk}),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(cannot_deactivate_admin.status_code, 404)
        self.assertEqual(response.status_code, 200)
        delegated.refresh_from_db()
        broker.refresh_from_db()
        self.assertTrue(delegated.is_active)
        self.assertFalse(broker.is_active)
        self.client.force_authenticate(user=delegated)
        self.assertEqual(
            self.client.get(reverse('api:admin-delegated-account-list')).status_code,
            200,
        )
        self.client.force_authenticate(user=broker)
        self.assertEqual(
            self.client.get(reverse('api:admin-delegated-account-list')).status_code,
            403,
        )

    def test_broker_can_reject_a_listing_with_reason_and_audit(self):
        self.client.force_authenticate(user=self.create_broker('moderating-broker'))
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

    def test_broker_must_record_a_reason_when_suspending_a_listing(self):
        self.client.force_authenticate(user=self.create_broker('suspending-broker'))
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

    def test_broker_cannot_publish_a_sold_or_rented_listing(self):
        self.property.status = Property.Status.RENTED
        self.property.save()
        self.client.force_authenticate(user=self.create_broker('publication-broker'))

        response = self.client.patch(
            reverse('api:admin-property-detail', kwargs={'pk': self.property.pk}),
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_public_report_submission_hides_reporter_data_and_broker_can_review(self):
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
        reviewer = self.create_broker('report-review-broker')
        self.client.force_authenticate(user=reviewer)
        reviewed = self.client.patch(
            reverse('api:admin-report-detail', kwargs={'pk': report.pk}),
            {
                'status': ListingReport.Status.ACTION_TAKEN,
                'moderator_notes': 'Owner contacted to verify details.',
            },
            format='json',
        )

        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.data['reviewed_by'], reviewer.pk)
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

    def test_broker_can_assign_only_approved_brokers_and_audit_assignment(self):
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
        assigning_broker = self.create_broker('broker-assignment-manager')
        self.client.force_authenticate(user=assigning_broker)

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
                granted_by=assigning_broker,
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
    def test_admin_tables_use_scrollable_regions_on_small_screens(self):
        owner = User.objects.create_superuser(
            username='responsive-admin-owner',
            password='SecurePass123!value',
        )
        client = Client()
        client.force_login(owner)

        for url in (reverse('admin_delegated_accounts'),):
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="table-scroll" role="region"')
                self.assertContains(response, 'class="table"')

    def test_server_rendered_portal_forms_include_csrf_tokens(self):
        owner = User.objects.create_superuser(
            username='csrf-form-owner',
            password='SecurePass123!value',
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(owner)

        rendered_token = None
        for url in (reverse('admin_delegated_accounts'),):
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 200)
                token_match = re.search(
                    rb'<input[^>]*name="csrfmiddlewaretoken"[^>]*value="([^"]+)"',
                    response.content,
                )
                self.assertIsNotNone(token_match)
                self.assertNotEqual(token_match.group(1), b'NOTPROVIDED')
                rendered_token = token_match.group(1).decode('ascii')

        response = client.post(
            reverse('admin_portal_logout'),
            HTTP_X_CSRFTOKEN=rendered_token,
        )
        self.assertRedirects(response, '/admin/login/')

    def test_superuser_portal_routes_to_broker_management_only(self):
        owner = User.objects.create_superuser(
            username='viewings-removed-owner',
            password='SecurePass123!value',
        )
        client = Client()
        client.force_login(owner)

        dashboard = client.get(reverse('admin_dashboard'))

        self.assertEqual(dashboard.status_code, 302)
        self.assertEqual(dashboard.url, '/admin-portal/delegated-accounts/')
        broker_page = client.get(reverse('admin_delegated_accounts'))
        self.assertEqual(broker_page.status_code, 200)
        self.assertNotContains(broker_page, '/admin-portal/properties/')
        self.assertNotContains(broker_page, 'viewing requests')
        self.assertEqual(client.get('/admin-portal/viewing-requests/').status_code, 404)

    def test_brokers_cannot_access_broker_account_management(self):
        broker = User.objects.create_user(
            username='broker-without-account-management',
            password='SecurePass123!value',
        )
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            ],
        )
        client = Client()
        client.force_login(broker)

        response = client.get(reverse('admin_delegated_accounts'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')
        self.assertNotIn(Profile.Permission.USERS_MANAGE, broker.profile.management_permissions)

    def test_portal_logout_requires_post_and_ends_session(self):
        owner = User.objects.create_superuser(
            username='portal-logout-owner',
            password='SecurePass123!value',
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(owner)

        page = client.get(reverse('admin_delegated_accounts'))
        self.assertContains(page, 'Log out')
        self.assertEqual(
            client.get(reverse('admin_portal_logout')).status_code,
            405,
        )
        self.assertEqual(
            client.post(reverse('admin_portal_logout')).status_code,
            403,
        )

        response = client.post(
            reverse('admin_portal_logout'),
            HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value,
        )

        self.assertRedirects(response, '/admin/login/')
        self.assertNotIn('_auth_user_id', client.session)
        self.assertEqual(client.get(reverse('admin_dashboard')).status_code, 302)

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
        self.assertEqual(
            set(invited.profile.management_permissions),
            {
                permission
                for permission, _ in Profile.Permission.choices
                if permission not in {
                    Profile.Permission.USERS_MANAGE,
                    Profile.Permission.STAFF_MANAGE,
                }
            },
        )
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

    @override_settings(DEBUG=True)
    def test_local_opaque_origin_invitation_requires_valid_csrf_token(self):
        owner = User.objects.create_superuser(
            username='opaque-origin-owner',
            password='SecurePass123!value',
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(owner)
        form_page = client.get(reverse('admin_delegated_accounts'))
        self.assertEqual(form_page.status_code, 200)
        csrf_token = client.cookies['csrftoken'].value
        payload = {
            'username': 'opaque-origin-broker',
            'email': 'opaque-origin-broker@example.com',
            'role': Profile.Role.BROKER,
            'management_permissions': [Profile.Permission.PROPERTY_MANAGE_ASSIGNED],
        }

        invalid = client.post(
            reverse('admin_delegated_accounts'),
            payload,
            HTTP_ORIGIN='null',
            HTTP_X_CSRFTOKEN='invalid',
        )
        self.assertEqual(invalid.status_code, 403)
        self.assertFalse(User.objects.filter(username='opaque-origin-broker').exists())

        accepted = client.post(
            reverse('admin_delegated_accounts'),
            {
                **payload,
                'username': 'valid-opaque-origin-broker',
                'email': 'valid-opaque@example.com',
                'csrfmiddlewaretoken': csrf_token,
            },
            HTTP_ORIGIN='null',
        )
        self.assertEqual(
            accepted.status_code,
            200,
            accepted.wsgi_request.META.get('CSRF_FAILURE_REASON', ''),
        )
        self.assertTrue(User.objects.filter(username='valid-opaque-origin-broker').exists())

    def test_null_origin_is_not_allowed_on_other_portal_post_routes(self):
        owner = User.objects.create_superuser(
            username='other-origin-owner',
            password='SecurePass123!value',
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(owner)
        client.get(reverse('admin_delegated_accounts'))

        response = client.post(
            reverse('admin_portal_logout'),
            HTTP_ORIGIN='null',
            HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value,
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=False)
    def test_null_origin_is_not_allowed_for_invitation_form_outside_debug(self):
        owner = User.objects.create_superuser(
            username='production-origin-owner',
            password='SecurePass123!value',
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(owner)
        client.get(reverse('admin_delegated_accounts'))

        response = client.post(
            reverse('admin_delegated_accounts'),
            {
                'username': 'production-origin-broker',
                'email': 'production-origin-broker@example.com',
                'role': Profile.Role.BROKER,
                'management_permissions': [Profile.Permission.PROPERTY_MANAGE_ASSIGNED],
                'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
            },
            HTTP_ORIGIN='null',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='production-origin-broker').exists())

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
        self.assertTrue(profile.management_permissions)
        self.assertNotIn(Profile.Permission.STAFF_MANAGE, profile.management_permissions)
        self.assertTrue(
            AdminAuditEvent.objects.filter(
                action='delegated_account_updated',
                object_id=str(delegated.pk),
            ).exists()
        )

    def test_legacy_property_mutation_routes_redirect_away_from_superuser(self):
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

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin-portal/delegated-accounts/')
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

    def test_superuser_cannot_toggle_property_through_legacy_portal(self):
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
        self.assertEqual(response.url, '/admin-portal/delegated-accounts/')
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, Property.Status.AVAILABLE)
        self.assertFalse(
            AdminAuditEvent.objects.filter(
                action='property_status_changed',
                object_id=str(property_obj.pk),
            ).exists()
        )
