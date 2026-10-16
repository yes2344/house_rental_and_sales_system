from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import EmailVerificationToken, Profile, TabSessionToken, UserPreferences
from accounts.permissions import (
    BROKER_WORK_PERMISSIONS,
    IsPropertyManagerOrAdministrator,
    IsViewingRequestManager,
    effective_management_permissions,
    has_management_permission,
)
from favorites.models import Favorite
from properties.models import Location, Property, PropertyBrokerAssignment
from viewings.models import ViewingRequest


class ProfileConstraintTests(TestCase):
    def test_broker_approval_is_rejected_for_non_broker(self):
        user = get_user_model().objects.create_user(username='property-owner')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Profile.objects.create(user=user, role=Profile.Role.OWNER, broker_approved=True)


class AccountApiTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def create_assigned_city(self):
        country = Location.objects.create(
            name='Account Test Country',
            slug='account-test-country',
            location_type=Location.Type.COUNTRY,
        )
        return Location.objects.create(
            name='Account Test City',
            slug='account-test-city',
            location_type=Location.Type.CITY,
            parent=country,
        )

    def test_provisioned_broker_must_change_password_then_complete_profile_before_access(self):
        city = self.create_assigned_city()
        broker = get_user_model().objects.create_user(
            username='provisioned-broker',
            password='Temp!BrokerLogin9281',
        )
        profile = Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            assigned_city=city,
            broker_approved=False,
            broker_onboarding_required=True,
            broker_password_changed=False,
            management_permissions=list(BROKER_WORK_PERMISSIONS),
        )
        self.client.force_authenticate(user=broker)

        before_setup = self.client.get(reverse('api:managed-property-list'))
        profile_before_password = self.client.post(
            reverse('api:broker-onboarding-profile'),
            {
                'first_name': 'Broker',
                'last_name': 'Example',
                'email': 'broker@example.com',
                'phone': '+251911111111',
            },
            format='json',
        )
        self.assertEqual(before_setup.status_code, 403)
        self.assertEqual(profile_before_password.status_code, 400)

        password_changed = self.client.post(
            reverse('api:broker-onboarding-password'),
            {
                'username': 'provisioned-broker-new',
                'new_password': 'Changed!BrokerPassword8294',
            },
            format='json',
        )
        broker.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(password_changed.status_code, 200)
        self.assertEqual(broker.username, 'provisioned-broker-new')
        self.assertTrue(broker.check_password('Changed!BrokerPassword8294'))
        self.assertTrue(profile.broker_onboarding_required)
        self.assertTrue(profile.broker_password_changed)
        self.assertFalse(profile.broker_approved)
        self.assertEqual(password_changed.data['management_permissions'], [])

        profile_completed = self.client.post(
            reverse('api:broker-onboarding-profile'),
            {
                'first_name': 'Broker',
                'last_name': 'Example',
                'email': 'broker@example.com',
                'phone': '+251911111111',
            },
            format='json',
        )
        broker.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(profile_completed.status_code, 200)
        self.assertEqual(profile_completed.data['broker_onboarding_required'], False)
        self.assertFalse(profile.broker_onboarding_required)
        self.assertTrue(profile.broker_approved)
        self.assertEqual(profile.phone, '+251911111111')
        self.assertEqual(broker.email, 'broker@example.com')
        self.assertEqual(set(effective_management_permissions(broker)), BROKER_WORK_PERMISSIONS)
        self.assertEqual(self.client.get(reverse('api:managed-property-list')).status_code, 200)

    def test_provisioned_broker_can_keep_username_and_duplicate_email_is_rejected(self):
        city = self.create_assigned_city()
        broker = get_user_model().objects.create_user(
            username='onboarding-broker',
            password='Temp!BrokerLogin9281',
        )
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            assigned_city=city,
            broker_onboarding_required=True,
            broker_password_changed=False,
        )
        self.client.force_authenticate(user=broker)
        password_changed = self.client.post(
            reverse('api:broker-onboarding-password'),
            {'new_password': 'Changed!BrokerPassword8294'},
            format='json',
        )
        self.assertEqual(password_changed.status_code, 200)
        self.assertEqual(password_changed.data['username'], 'onboarding-broker')

        get_user_model().objects.create_user(username='other-account', email='taken@example.com')
        duplicate_email = self.client.post(
            reverse('api:broker-onboarding-profile'),
            {
                'first_name': 'Broker',
                'last_name': 'Example',
                'email': 'taken@example.com',
                'phone': '+251911111111',
            },
            format='json',
        )
        self.assertEqual(duplicate_email.status_code, 400)
        self.assertTrue(broker.profile.broker_onboarding_required)

    def test_django_superuser_can_sign_in_through_the_shared_account_endpoint(self):
        administrator = get_user_model().objects.create_superuser(
            username='shared-login-django-admin',
            password='SecurePass123!value',
        )

        response = self.client.post(
            reverse('api:login'),
            {'username': administrator.username, 'password': 'SecurePass123!value'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], administrator.username)
        self.assertEqual(
            response.data['management_permissions'],
            [
                Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW,
                Profile.Permission.SETTINGS_MANAGE,
                Profile.Permission.BRANDING_MANAGE,
                Profile.Permission.LOCATIONS_MANAGE_CITIES,
                Profile.Permission.STAFF_MANAGE,
            ],
        )
        self.assertTrue(response.data['is_platform_owner'])

    def test_django_superuser_has_the_same_platform_role_as_delegated_administrator(self):
        administrator = get_user_model().objects.create_superuser(
            username='django-admin-only',
            password='SecurePass123!value',
        )
        self.client.force_authenticate(user=administrator)

        response = self.client.get(reverse('api:me'))
        broker_admin = get_user_model().objects.create_user(
            username='delegated-admin',
            is_staff=True,
        )
        Profile.objects.create(
            user=broker_admin,
            role=Profile.Role.ADMINISTRATOR,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], Profile.Role.ADMINISTRATOR)
        self.assertEqual(
            [
                permission
                for permission in response.data['management_permissions']
                if permission != Profile.Permission.SETTINGS_MANAGE
            ],
            effective_management_permissions(broker_admin),
        )
        self.assertTrue(response.data['is_platform_owner'])
        self.assertFalse(has_management_permission(administrator, Profile.Permission.USERS_MANAGE))
        self.assertFalse(has_management_permission(administrator, Profile.Permission.PROPERTY_VIEW_ALL))
        self.assertFalse(has_management_permission(administrator, Profile.Permission.VIEWING_VIEW_ALL))
        self.assertTrue(has_management_permission(administrator, Profile.Permission.SETTINGS_MANAGE))
        self.assertTrue(has_management_permission(administrator, Profile.Permission.BRANDING_MANAGE))
        self.assertFalse(has_management_permission(administrator, Profile.Permission.AUDIT_VIEW))
        self.assertFalse(has_management_permission(administrator, Profile.Permission.REPORTS_REVIEW))
        self.assertFalse(has_management_permission(administrator, Profile.Permission.BROKERS_ASSIGN))
        self.assertTrue(has_management_permission(administrator, Profile.Permission.STAFF_MANAGE))
        self.assertTrue(has_management_permission(administrator, Profile.Permission.LOCATIONS_MANAGE_CITIES))
        self.assertFalse(has_management_permission(administrator, Profile.Permission.LOCATIONS_MANAGE_SUBCITIES))
        self.assertEqual(
            self.client.get(reverse('api:admin-property-list')).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('api:managed-property-list')).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('api:managed-viewing-list')).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('api:managed-location-list')).status_code,
            200,
        )

    def test_approved_broker_role_has_all_marketplace_permissions_except_account_control(self):
        broker = get_user_model().objects.create_user(username='full-access-broker')
        profile = Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.PROPERTY_MANAGE_ASSIGNED],
        )

        self.assertEqual(set(effective_management_permissions(broker)), BROKER_WORK_PERMISSIONS)
        self.assertNotIn(Profile.Permission.USERS_MANAGE, effective_management_permissions(broker))
        self.assertNotIn(Profile.Permission.STAFF_MANAGE, effective_management_permissions(broker))
        self.assertNotIn(Profile.Permission.AUDIT_VIEW, effective_management_permissions(broker))
        self.assertIn(Profile.Permission.LOCATIONS_MANAGE_SUBCITIES, effective_management_permissions(broker))
        self.assertNotIn(Profile.Permission.LOCATIONS_MANAGE_CITIES, effective_management_permissions(broker))
        self.assertNotIn(Profile.Permission.REPORTS_REVIEW, effective_management_permissions(broker))
        self.assertNotIn(Profile.Permission.BROKERS_ASSIGN, effective_management_permissions(broker))
        self.assertNotIn(Profile.Permission.USERS_MANAGE, profile.management_permissions)

    def test_agent_settings_permission_is_effective_only_when_explicitly_granted(self):
        broker = get_user_model().objects.create_user(username='settings-permission-agent')
        profile = Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.SETTINGS_MANAGE],
        )

        self.assertTrue(has_management_permission(broker, Profile.Permission.SETTINGS_MANAGE))
        self.assertIn(Profile.Permission.SETTINGS_MANAGE, effective_management_permissions(broker))
        profile.broker_approved = False
        profile.save(update_fields=['broker_approved'])
        self.assertFalse(has_management_permission(broker, Profile.Permission.SETTINGS_MANAGE))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        PUBLIC_FRONTEND_URL='https://frontend.example',
    )
    def test_registration_creates_inactive_customer_and_ignores_client_role(self):
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
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.role, Profile.Role.CUSTOMER)
        self.assertFalse(user.profile.broker_approved)
        self.assertEqual(response.data['role'], Profile.Role.CUSTOMER)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_registration_rejects_external_return_paths(self):
        response = self.client.post(
            reverse('api:register'),
            {
                'username': 'unsafe-return-customer',
                'email': 'unsafe-return@example.com',
                'password': 'Evergreen!Place42',
                'next_path': '//outside.example/path',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='unsafe-return-customer').exists())

    @staticmethod
    def _last_email_query(path):
        link = next(
            line.strip()
            for line in reversed(mail.outbox[-1].body.splitlines())
            if line.strip().startswith('https://')
        )
        parsed = urlsplit(link)
        if parsed.path != path:
            raise AssertionError(f'Expected an email link to {path}, received {parsed.path}.')
        return {key: values[0] for key, values in parse_qs(parsed.query).items()}

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        PUBLIC_FRONTEND_URL='https://frontend.example',
    )
    def test_email_verification_activates_account_and_preserves_safe_return_path(self):
        response = self.client.post(
            reverse('api:register'),
            {
                'username': 'email-verified-customer',
                'email': 'verified@example.com',
                'password': 'Evergreen!Place42',
                'phone': '+251900000001',
                'next_path': '/submissions/new',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username='email-verified-customer')
        self.assertFalse(user.is_active)

        params = self._last_email_query('/verify-email')
        self.assertEqual(params['next'], '/submissions/new')
        verified = self.client.post(reverse('api:verify-email'), params, format='json')
        self.assertEqual(verified.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertFalse(EmailVerificationToken.objects.filter(user=user).exists())

        reused = self.client.post(reverse('api:verify-email'), params, format='json')
        self.assertEqual(reused.status_code, 400)
        email_login = self.client.post(
            reverse('api:login'),
            {'identifier': 'verified@example.com', 'password': 'Evergreen!Place42'},
            format='json',
        )
        self.assertEqual(email_login.status_code, 200)
        protected_agent_api = self.client.get(
            reverse('api:managed-property-list'),
            HTTP_AUTHORIZATION=f"Bearer {email_login.data['session_token']}",
        )
        self.assertEqual(protected_agent_api.status_code, 403)

        phone_login = self.client.post(
            reverse('api:login'),
            {'identifier': '+251900000001', 'password': 'Evergreen!Place42'},
            format='json',
        )
        self.assertEqual(phone_login.status_code, 200)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        PUBLIC_FRONTEND_URL='https://frontend.example',
    )
    def test_expired_verification_link_does_not_activate_account(self):
        self.client.post(
            reverse('api:register'),
            {
                'username': 'expired-verification-customer',
                'email': 'expired@example.com',
                'password': 'Evergreen!Place42',
            },
            format='json',
        )
        user = get_user_model().objects.get(username='expired-verification-customer')
        EmailVerificationToken.objects.filter(user=user).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        response = self.client.post(
            reverse('api:verify-email'),
            self._last_email_query('/verify-email'),
            format='json',
        )
        user.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(user.is_active)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        PUBLIC_FRONTEND_URL='https://frontend.example',
    )
    def test_resend_does_not_reactivate_preexisting_inactive_accounts(self):
        customer = get_user_model().objects.create_user(
            username='deactivated-customer',
            email='deactivated-customer@example.com',
            is_active=False,
        )
        agent = get_user_model().objects.create_user(
            username='inactive-agent',
            email='inactive-agent@example.com',
            is_active=False,
        )
        Profile.objects.create(user=customer, role=Profile.Role.CUSTOMER)
        Profile.objects.create(user=agent, role=Profile.Role.BROKER)

        for email in (customer.email, agent.email):
            response = self.client.post(
                reverse('api:resend-verification-email'),
                {'email': email},
                format='json',
            )
            self.assertEqual(response.status_code, 202)

        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EmailVerificationToken.objects.exists())
        customer.refresh_from_db()
        agent.refresh_from_db()
        self.assertFalse(customer.is_active)
        self.assertFalse(agent.is_active)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        PUBLIC_FRONTEND_URL='https://frontend.example',
    )
    def test_password_reset_link_changes_password_once(self):
        user = get_user_model().objects.create_user(
            username='password-reset-customer',
            email='password-reset@example.com',
            password='Old!Password9283',
        )
        Profile.objects.create(user=user, role=Profile.Role.CUSTOMER, phone='+251900000002')
        response = self.client.post(
            reverse('api:password-reset-request'),
            {'email': user.email},
            format='json',
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        session, token = TabSessionToken.issue(user)
        params = self._last_email_query('/reset-password')
        params.update({
            'password': 'New!Password9283',
            'password_confirmation': 'New!Password9283',
        })
        reset = self.client.post(
            reverse('api:password-reset-confirm'),
            params,
            format='json',
        )
        self.assertEqual(reset.status_code, 200)
        user.refresh_from_db()
        session.refresh_from_db()
        self.assertTrue(user.check_password('New!Password9283'))
        self.assertIsNotNone(session.revoked_at)

        revoked_session = self.client.get(
            reverse('api:managed-property-list'),
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertIn(revoked_session.status_code, (401, 403))

        reused = self.client.post(
            reverse('api:password-reset-confirm'),
            params,
            format='json',
        )
        self.assertEqual(reused.status_code, 400)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        PUBLIC_FRONTEND_URL='https://frontend.example',
        PASSWORD_RESET_TIMEOUT=-1,
    )
    def test_expired_password_reset_link_is_rejected(self):
        user = get_user_model().objects.create_user(
            username='expired-reset-customer',
            email='expired-reset@example.com',
            password='Old!Password9283',
        )
        response = self.client.post(
            reverse('api:password-reset-request'),
            {'email': user.email},
            format='json',
        )
        self.assertEqual(response.status_code, 202)
        params = self._last_email_query('/reset-password')
        params.update({
            'password': 'New!Password9283',
            'password_confirmation': 'New!Password9283',
        })
        rejected = self.client.post(
            reverse('api:password-reset-confirm'),
            params,
            format='json',
        )
        user.refresh_from_db()
        self.assertEqual(rejected.status_code, 400)
        self.assertTrue(user.check_password('Old!Password9283'))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        PUBLIC_FRONTEND_URL='https://frontend.example',
    )
    def test_unverified_users_cannot_login_or_reuse_manually_issued_session_tokens(self):
        self.client.post(
            reverse('api:register'),
            {
                'username': 'unverified-customer',
                'email': 'unverified@example.com',
                'password': 'Evergreen!Place42',
            },
            format='json',
        )
        user = get_user_model().objects.get(username='unverified-customer')
        login = self.client.post(
            reverse('api:login'),
            {'username': user.email, 'password': 'Evergreen!Place42'},
            format='json',
        )
        _, token = TabSessionToken.issue(user)
        protected = self.client.get(
            reverse('api:managed-property-list'),
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(login.status_code, 400)
        self.assertIn(protected.status_code, (401, 403))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        PUBLIC_FRONTEND_URL='https://frontend.example',
    )
    def test_password_reset_response_does_not_disclose_unknown_email(self):
        user = get_user_model().objects.create_user(
            username='reset-enumeration-customer',
            email='reset-enumeration@example.com',
            password='Evergreen!Place42',
        )
        known = self.client.post(
            reverse('api:password-reset-request'),
            {'email': user.email},
            format='json',
        )
        unknown = self.client.post(
            reverse('api:password-reset-request'),
            {'email': 'missing@example.com'},
            format='json',
        )
        self.assertEqual(known.status_code, 202)
        self.assertEqual(unknown.status_code, 202)
        self.assertEqual(known.data['detail'], unknown.data['detail'])

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

    def test_malformed_json_returns_standard_api_error(self):
        response = self.client.post(
            reverse('api:login'),
            data='{"username":',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['status_code'], 400)
        self.assertIsInstance(response.data['error']['message'], str)

    def test_unknown_account_and_incorrect_password_share_login_error(self):
        user = get_user_model().objects.create_user(
            username='known-login-account',
            password='Evergreen!Place42',
        )
        responses = [
            self.client.post(
                reverse('api:login'),
                {'username': user.username, 'password': 'incorrect-password'},
                format='json',
            ),
            self.client.post(
                reverse('api:login'),
                {'username': 'unknown-login-account', 'password': 'incorrect-password'},
                format='json',
            ),
        ]

        self.assertEqual([response.status_code for response in responses], [400, 400])
        self.assertEqual(
            responses[0].data['error']['details'],
            responses[1].data['error']['details'],
        )
        self.assertEqual(
            responses[0].data['error']['details']['non_field_errors'],
            ['Invalid username or password.'],
        )

    def test_login_rejects_missing_credentials(self):
        response = self.client.post(reverse('api:login'), {}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['status_code'], 400)
        self.assertIn('username', response.data['error']['details'])
        self.assertIn('password', response.data['error']['details'])

    def test_expired_tab_token_cannot_access_authenticated_account(self):
        user = get_user_model().objects.create_user(username='expired-token-account')
        session, token = TabSessionToken.issue(user)
        TabSessionToken.objects.filter(pk=session.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        for supplied_token in (token, 'not-a-valid-token'):
            with self.subTest(token_type='expired' if supplied_token == token else 'invalid'):
                response = self.client.get(
                    reverse('api:me'),
                    HTTP_AUTHORIZATION=f'Bearer {supplied_token}',
                )

                self.assertIn(response.status_code, [401, 403])

    def test_login_requires_csrf_token_and_returns_tab_session_token(self):
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
        self.assertNotIn('sessionid', client.cookies)
        self.assertIn('session_token', response.data)
        self.assertIn('csrf_token', response.data)

        logout_response = client.post(
            reverse('api:logout'),
            {},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {response.data['session_token']}",
        )
        self.assertEqual(logout_response.status_code, 204)
        account_after_logout = client.get(reverse('api:me'))
        self.assertIn(account_after_logout.status_code, [401, 403])

    def test_logins_issue_isolated_tokens_and_logout_revokes_only_current_tab(self):
        user = get_user_model().objects.create_user(
            username='tab-isolated-customer',
            password='Evergreen!Place42',
        )
        Profile.objects.create(user=user)
        first_tab = APIClient()
        second_tab = APIClient()
        credentials = {'username': user.username, 'password': 'Evergreen!Place42'}

        first_login = first_tab.post(reverse('api:login'), credentials, format='json')
        second_login = second_tab.post(reverse('api:login'), credentials, format='json')

        self.assertEqual(first_login.status_code, 200)
        self.assertEqual(second_login.status_code, 200)
        first_token = first_login.data['session_token']
        second_token = second_login.data['session_token']
        self.assertNotEqual(first_token, second_token)
        self.assertFalse(TabSessionToken.objects.filter(token_digest=first_token).exists())

        first_account = first_tab.get(
            reverse('api:me'),
            HTTP_AUTHORIZATION=f'Bearer {first_token}',
        )
        second_account = second_tab.get(
            reverse('api:me'),
            HTTP_AUTHORIZATION=f'Bearer {second_token}',
        )
        self.assertEqual(first_account.status_code, 200)
        self.assertEqual(second_account.status_code, 200)

        revoked = first_tab.post(
            reverse('api:logout'),
            {},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {first_token}',
        )
        self.assertEqual(revoked.status_code, 204)
        self.assertIn(
            first_tab.get(
                reverse('api:me'),
                HTTP_AUTHORIZATION=f'Bearer {first_token}',
            ).status_code,
            [401, 403],
        )
        self.assertEqual(
            second_tab.get(
                reverse('api:me'),
                HTTP_AUTHORIZATION=f'Bearer {second_token}',
            ).status_code,
            200,
        )

        cookie_only_tab = APIClient()
        cookie_only_tab.force_login(user)
        self.assertIn(cookie_only_tab.get(reverse('api:me')).status_code, [401, 403])

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
        country = Location.objects.create(
            name='Object Permission Country',
            slug='object-permission-country',
            location_type=Location.Type.COUNTRY,
        )
        city = Location.objects.create(
            name='Object Permission City',
            slug='object-permission-city',
            location_type=Location.Type.CITY,
            parent=country,
        )
        subcity = Location.objects.create(
            name='Object Permission Subcity',
            slug='object-permission-subcity',
            location_type=Location.Type.SUBCITY,
            parent=city,
        )
        Profile.objects.create(
            user=self.broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=city,
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
            administrative_location=subcity,
            price=100000,
            description='A test listing.',
            owner=self.owner,
        )
        PropertyBrokerAssignment.objects.create(property=self.property, broker=self.broker)
        PropertyBrokerAssignment.objects.create(property=self.property, broker=self.unapproved_broker)

    def test_approved_broker_can_manage_only_assigned_or_same_city_properties(self):
        permission = IsPropertyManagerOrAdministrator()

        def request_for(user):
            return type('Request', (), {'user': user})()

        self.assertFalse(permission.has_object_permission(request_for(self.owner), None, self.property))
        self.assertTrue(permission.has_object_permission(request_for(self.broker), None, self.property))
        unassigned_property = Property.objects.create(
            title='Unassigned marketplace property',
            location='Another area',
            price=120000,
            description='Managed within the same marketplace.',
            administrative_location=self.property.administrative_location,
        )
        self.assertTrue(
            permission.has_object_permission(request_for(self.broker), None, unassigned_property)
        )
        other_city = Location.objects.create(
            name='Object Permission Other City',
            slug='object-permission-other-city',
            location_type=Location.Type.CITY,
            parent=self.property.administrative_location.parent.parent,
        )
        other_subcity = Location.objects.create(
            name='Object Permission Other Subcity',
            slug='object-permission-other-subcity',
            location_type=Location.Type.SUBCITY,
            parent=other_city,
        )
        cross_city_property = Property.objects.create(
            title='Cross city property',
            location='Another city',
            price=140000,
            description='Not managed by this city broker.',
            administrative_location=other_subcity,
        )
        self.assertFalse(
            permission.has_object_permission(request_for(self.broker), None, cross_city_property)
        )
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

    def test_broker_activity_does_not_include_customer_viewing_requests(self):
        broker = get_user_model().objects.create_user(username='activity-broker')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
        )
        property_obj = Property.objects.create(
            title='Broker activity property',
            slug='broker-activity-property',
            location='Submitted location',
            price=100000,
            description='A test listing.',
        )
        ViewingRequest.objects.create(
            property=property_obj,
            requester=broker,
            full_name='Broker Account',
            email='broker@example.com',
            phone='+251900000000',
            preferred_date='2026-11-01',
        )
        self.client.force_authenticate(user=broker)

        response = self.client.get(reverse('api:activity'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['viewing_requests'], [])


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
