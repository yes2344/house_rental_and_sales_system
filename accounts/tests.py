from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from accounts.models import Profile, UserPreferences
from accounts.permissions import IsPropertyManagerOrAdministrator, IsViewingRequestManager
from favorites.models import Favorite
from properties.models import Property, PropertyBrokerAssignment
from viewings.models import ViewingRequest


class ProfileConstraintTests(TestCase):
    def test_broker_approval_is_rejected_for_non_broker(self):
        user = get_user_model().objects.create_user(username='property-owner')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Profile.objects.create(user=user, role=Profile.Role.OWNER, broker_approved=True)


class AccountApiTests(APITestCase):
    def test_registration_creates_customer_and_ignores_client_role(self):
        response = self.client.post(
            reverse('api:register'),
            {
                'username': 'new-customer',
                'email': 'customer@example.com',
                'password': 'Evergreen!Place42',
                'phone': '+251900000000',
                'role': 'broker',
                'broker_approved': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username='new-customer')
        self.assertTrue(user.check_password('Evergreen!Place42'))
        self.assertEqual(user.profile.role, Profile.Role.CUSTOMER)
        self.assertFalse(user.profile.broker_approved)
        self.assertEqual(response.data['role'], Profile.Role.CUSTOMER)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse('api:register'),
            {
                'username': 'weak-password-user',
                'email': 'weak@example.com',
                'password': 'password',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data['error']['details'])

    def test_login_requires_csrf_token_and_establishes_session(self):
        user = get_user_model().objects.create_user(
            username='csrf-customer',
            email='csrf@example.com',
            password='Evergreen!Place42',
        )
        Profile.objects.create(user=user)
        client = APIClient(enforce_csrf_checks=True)

        blocked = client.post(
            reverse('api:login'),
            {'username': user.username, 'password': 'Evergreen!Place42'},
            format='json',
        )
        self.assertEqual(blocked.status_code, 403)

        csrf_response = client.get(reverse('api:csrf-token'))
        self.assertEqual(csrf_response.status_code, 200)
        token = csrf_response.data['csrf_token']
        response = client.post(
            reverse('api:login'),
            {'username': user.username, 'password': 'Evergreen!Place42'},
            format='json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], user.username)
        self.assertIn('sessionid', client.cookies)
        self.assertIn('csrf_token', response.data)

        logout_response = client.post(
            reverse('api:logout'),
            {},
            format='json',
            HTTP_X_CSRFTOKEN=response.data['csrf_token'],
        )
        self.assertEqual(logout_response.status_code, 204)

    def test_profile_update_cannot_change_role(self):
        user = get_user_model().objects.create_user(
            username='profile-customer',
            password='Evergreen!Place42',
        )
        Profile.objects.create(user=user, role=Profile.Role.CUSTOMER)
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            reverse('api:me'),
            {'phone': '+251911111111', 'role': 'broker'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.role, Profile.Role.CUSTOMER)
        self.assertEqual(user.profile.phone, '+251911111111')

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('api:me'))

        self.assertNotEqual(response.status_code, 200)
        self.assertIn(response.status_code, [401, 403])


class ListingObjectPermissionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username='listing-owner')
        Profile.objects.create(user=self.owner, role=Profile.Role.OWNER)
        self.other_customer = user_model.objects.create_user(username='other-customer')
        Profile.objects.create(user=self.other_customer, role=Profile.Role.CUSTOMER)
        self.broker = user_model.objects.create_user(username='approved-broker')
        Profile.objects.create(
            user=self.broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            ],
        )
        self.unapproved_broker = user_model.objects.create_user(username='unapproved-broker')
        Profile.objects.create(
            user=self.unapproved_broker,
            role=Profile.Role.BROKER,
            broker_approved=False,
        )
        self.property = Property.objects.create(
            title='Permission Test Property',
            location='Submitted location',
            price=100000,
            description='A test listing.',
            owner=self.owner,
        )
        PropertyBrokerAssignment.objects.create(property=self.property, broker=self.broker)
        PropertyBrokerAssignment.objects.create(property=self.property, broker=self.unapproved_broker)

    def test_only_owner_or_approved_assigned_broker_can_manage_property(self):
        permission = IsPropertyManagerOrAdministrator()

        def request_for(user):
            return type('Request', (), {'user': user})()

        self.assertTrue(permission.has_object_permission(request_for(self.owner), None, self.property))
        self.assertTrue(permission.has_object_permission(request_for(self.broker), None, self.property))
        self.assertFalse(
            permission.has_object_permission(request_for(self.unapproved_broker), None, self.property)
        )
        self.assertFalse(
            permission.has_object_permission(request_for(self.other_customer), None, self.property)
        )

    def test_viewing_request_permission_checks_property_manager(self):
        permission = IsViewingRequestManager()
        viewing = ViewingRequest.objects.create(
            property=self.property,
            full_name='Visitor',
            email='visitor@example.com',
            phone='+251900000000',
            preferred_date='2026-11-01',
        )
        request = type('Request', (), {'user': self.other_customer})()

        self.assertFalse(permission.has_object_permission(request, None, viewing))


class AccountActivityApiTests(APITestCase):
    def test_activity_contains_only_authenticated_users_own_records_and_omits_pii(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username='activity-user')
        other_user = user_model.objects.create_user(username='activity-other-user')
        property_obj = Property.objects.create(
            title='Activity property',
            slug='activity-property-api',
            location='Submitted location',
            price=100000,
            description='A test listing.',
        )
        Favorite.objects.create(user=user, property=property_obj)
        own_request = ViewingRequest.objects.create(
            property=property_obj,
            requester=user,
            full_name='Activity User',
            email='private@example.com',
            phone='+251900000000',
            preferred_date='2026-11-01',
        )
        ViewingRequest.objects.create(
            property=property_obj,
            requester=other_user,
            full_name='Other User',
            email='other@example.com',
            phone='+251911111111',
            preferred_date='2026-11-02',
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse('api:activity'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['favorites']), 1)
        self.assertEqual(len(response.data['viewing_requests']), 1)
        self.assertEqual(response.data['viewing_requests'][0]['id'], own_request.pk)
        self.assertNotIn('email', response.data['viewing_requests'][0])
        self.assertNotIn('phone', response.data['viewing_requests'][0])


class AccountPreferencesApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.first_user = user_model.objects.create_user(username='preferences-first')
        Profile.objects.create(user=self.first_user, role=Profile.Role.CUSTOMER)
        self.second_user = user_model.objects.create_user(username='preferences-second')
        Profile.objects.create(user=self.second_user, role=Profile.Role.CUSTOMER)

    def test_authenticated_user_reads_and_updates_only_their_preferences(self):
        self.client.force_authenticate(user=self.first_user)

        initial = self.client.get(reverse('api:preferences'))
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(initial.data, {
            'theme': UserPreferences.Theme.SYSTEM,
            'locale': UserPreferences.Locale.ENGLISH,
            'density': UserPreferences.Density.COMFORTABLE,
            'reduced_motion': False,
        })

        updated = self.client.patch(
            reverse('api:preferences'),
            {'theme': 'dark', 'locale': 'am', 'reduced_motion': True},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['theme'], UserPreferences.Theme.DARK)
        self.assertEqual(updated.data['locale'], UserPreferences.Locale.AMHARIC)
        self.assertTrue(updated.data['reduced_motion'])
        self.assertFalse(UserPreferences.objects.filter(user=self.second_user).exists())

        self.client.force_authenticate(user=self.second_user)
        second_user_preferences = self.client.get(reverse('api:preferences'))
        self.assertEqual(second_user_preferences.status_code, 200)
        self.assertEqual(second_user_preferences.data['theme'], UserPreferences.Theme.SYSTEM)

    def test_unsupported_fields_and_values_are_rejected(self):
        self.client.force_authenticate(user=self.first_user)

        protected_field = self.client.patch(
            reverse('api:preferences'),
            {'theme': 'dark', 'role': 'administrator', 'management_permissions': ['settings.manage']},
            format='json',
        )
        invalid_choice = self.client.patch(
            reverse('api:preferences'),
            {'theme': 'sepia'},
            format='json',
        )

        self.assertEqual(protected_field.status_code, 400)
        self.assertEqual(invalid_choice.status_code, 400)
        self.assertEqual(self.first_user.profile.role, Profile.Role.CUSTOMER)
        self.assertFalse(UserPreferences.objects.filter(user=self.first_user).exists())

    def test_reset_changes_only_the_current_users_preferences(self):
        first_preferences = UserPreferences.objects.create(
            user=self.first_user,
            theme=UserPreferences.Theme.DARK,
            locale=UserPreferences.Locale.AMHARIC,
            density=UserPreferences.Density.COMPACT,
            reduced_motion=True,
        )
        second_preferences = UserPreferences.objects.create(
            user=self.second_user,
            theme=UserPreferences.Theme.LIGHT,
        )
        self.client.force_authenticate(user=self.first_user)

        response = self.client.post(reverse('api:preferences-reset'), {}, format='json')

        self.assertEqual(response.status_code, 200)
        first_preferences.refresh_from_db()
        second_preferences.refresh_from_db()
        self.assertEqual(first_preferences.theme, UserPreferences.Theme.SYSTEM)
        self.assertEqual(first_preferences.locale, UserPreferences.Locale.ENGLISH)
        self.assertEqual(first_preferences.density, UserPreferences.Density.COMFORTABLE)
        self.assertFalse(first_preferences.reduced_motion)
        self.assertEqual(second_preferences.theme, UserPreferences.Theme.LIGHT)

    def test_preferences_require_authentication(self):
        response = self.client.get(reverse('api:preferences'))
        self.assertIn(response.status_code, [401, 403])
