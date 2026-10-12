from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from owner_announcements.models import InAppNotification, OwnerAnnouncement
from properties.models import Property


User = get_user_model()


class RetiredOwnerAnnouncementWorkflowTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='legacy-owner',
            email='legacy-owner@example.test',
            password='secure-password-123',
        )
        self.property = Property.objects.create(
            title='Historical owner listing',
            location='Recorded location',
            property_type='house',
            listing_type=Property.ListingType.SALE,
            price='2500000.00',
            description='Historical record retained after owner submissions were retired.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
            service_type=Property.ServiceType.OWNER_ANNOUNCED,
            submitted_by=self.customer,
        )
        self.announcement = OwnerAnnouncement.objects.create(
            property=self.property,
            submitter=self.customer,
            owner_contact_name='Legacy Owner',
            owner_contact_phone='+251900000001',
            authorization_confirmed=True,
            terms_accepted_at=timezone.now(),
        )

    def test_owner_submission_and_review_endpoints_are_not_routable(self):
        retired_paths = [
            '/api/v1/owner/announcements/',
            '/api/v1/owner/announcements/1/',
            '/api/v1/owner/announcements/1/images/',
            '/api/v1/owner/announcements/1/renew/',
            '/api/v1/owner/announcements/1/withdraw/',
            '/api/v1/management/owner-announcements/',
            '/api/v1/management/owner-announcements/1/',
            '/api/v1/management/owner-announcements/1/decision/',
            '/api/v1/management/owner-announcements/1/renewal/',
            '/api/v1/management/owner-announcements/agreements/',
        ]
        for path in retired_paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, {}, format='json').status_code, 404)

    def test_historical_owner_announcement_and_property_are_retained_but_not_public(self):
        response = self.client.get(reverse('api:property-list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            self.property.pk,
            {item['id'] for item in response.data['results']},
        )
        self.assertTrue(OwnerAnnouncement.objects.filter(pk=self.announcement.pk).exists())
        self.assertTrue(Property.objects.filter(pk=self.property.pk).exists())
        self.assertEqual(self.property.publication_status, Property.PublicationStatus.PUBLISHED)

    def test_shared_notification_list_and_read_endpoints_remain_available(self):
        notification = InAppNotification.objects.create(
            recipient=self.customer,
            announcement=self.announcement,
            notification_type='viewing_request_update',
            message='A viewing request was updated.',
            idempotency_key='viewing-request-update:legacy-test',
        )
        self.client.force_authenticate(self.customer)

        response = self.client.get(reverse('api:notification-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['id'], notification.pk)

        read_response = self.client.post(reverse('api:notification-read', args=[notification.pk]))
        self.assertEqual(read_response.status_code, 200)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)
