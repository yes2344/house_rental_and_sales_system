from calendar import monthrange
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Profile
from owner_announcements.management.commands.process_owner_announcement_agreements import Command
from owner_announcements.models import (
    InAppNotification,
    OwnerAnnouncement,
    OwnerAnnouncementAgreement,
    OwnerAnnouncementEvent,
)
from properties.models import Location, Property


User = get_user_model()


class OwnerAnnouncementWorkflowTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner-one',
            email='owner@example.test',
            password='secure-password-123',
        )
        self.broker = User.objects.create_user(
            username='broker-one',
            email='broker@example.test',
            password='secure-password-123',
        )
        Profile.objects.create(
            user=self.broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW],
        )

    def submission_payload(self):
        return {
            'title': 'Owner submitted home',
            'location': 'Area provided by owner',
            'property_type': 'house',
            'listing_type': 'sale',
            'price': '2500000.00',
            'description': 'An owner submitted property for broker review.',
            'owner_contact_name': 'Owner One',
            'owner_contact_phone': '+251900000001',
            'owner_contact_email': 'owner@example.test',
            'authorization_confirmed': True,
            'terms_accepted': True,
        }

    def submit_announcement(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse('api:owner-announcement-list'),
            self.submission_payload(),
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        return OwnerAnnouncement.objects.get(pk=response.data['id'])

    def test_owner_submission_is_pending_and_not_public(self):
        announcement = self.submit_announcement()

        self.assertEqual(announcement.status, OwnerAnnouncement.Status.PENDING_REVIEW)
        self.assertEqual(
            announcement.property.publication_status,
            Property.PublicationStatus.PENDING_REVIEW,
        )
        public_response = self.client.get(reverse('api:property-list'))
        self.assertEqual(public_response.status_code, 200)
        self.assertFalse(any(
            item['id'] == announcement.property_id
            for item in public_response.data['results']
        ))

    def test_owner_submission_notifies_all_active_announcement_review_brokers(self):
        second_broker = User.objects.create_user(
            username='second-announcement-reviewer',
            password='secure-password-123',
        )
        Profile.objects.create(
            user=second_broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW],
        )
        inactive_broker = User.objects.create_user(
            username='inactive-announcement-reviewer',
            password='secure-password-123',
            is_active=False,
        )
        Profile.objects.create(
            user=inactive_broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
            management_permissions=[Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW],
        )
        unapproved_broker = User.objects.create_user(
            username='unapproved-broker',
            password='secure-password-123',
        )
        Profile.objects.create(
            user=unapproved_broker,
            role=Profile.Role.BROKER,
            broker_approved=False,
            management_permissions=[Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW],
        )

        announcement = self.submit_announcement()

        notified_users = set(InAppNotification.objects.filter(
            announcement=announcement,
            notification_type='announcement_submitted',
        ).values_list('recipient_id', flat=True))
        self.assertEqual(
            notified_users,
            {self.owner.pk, self.broker.pk, second_broker.pk},
        )
        self.client.force_authenticate(self.broker)
        broker_notifications = self.client.get(reverse('api:notification-list'))
        self.assertEqual(broker_notifications.status_code, 200)
        self.assertIn(announcement.pk, [
            notification['announcement_id']
            for notification in broker_notifications.data['results']
        ])

    def test_owner_resubmission_notifies_review_brokers_again(self):
        announcement = self.submit_announcement()
        self.client.force_authenticate(self.owner)

        response = self.client.patch(
            reverse('api:owner-announcement-detail', args=[announcement.pk]),
            {
                'description': 'Updated property details for another review.',
                'authorization_confirmed': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        notification = InAppNotification.objects.get(
            announcement=announcement,
            recipient=self.broker,
            notification_type='announcement_resubmitted',
        )
        self.assertIn('resubmitted property for review', notification.message)

    def test_only_a_broker_with_review_permission_can_approve(self):
        announcement = self.submit_announcement()
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse('api:management-owner-announcement-decision', args=[announcement.pk]),
            {'action': 'reject', 'feedback': 'Not authorized.'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_broker_managed_publication_endpoint_cannot_bypass_owner_review(self):
        announcement = self.submit_announcement()
        self.client.force_authenticate(self.broker)
        response = self.client.post(
            reverse('api:managed-property-publication', args=[announcement.property_id]),
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )
        self.assertEqual(response.status_code, 404)
        announcement.property.refresh_from_db()
        self.assertEqual(
            announcement.property.publication_status,
            Property.PublicationStatus.PENDING_REVIEW,
        )

    def test_approved_listing_is_public_but_contact_requires_agreement_choice(self):
        announcement = self.submit_announcement()
        start_date = timezone.localdate()
        months = 12
        month_index = start_date.month - 1 + months
        year = start_date.year + month_index // 12
        month = month_index % 12 + 1
        end_day = min(start_date.day, monthrange(year, month)[1])
        end_date = date(year, month, end_day) - timedelta(days=1)

        self.client.force_authenticate(self.broker)
        approval_response = self.client.post(
            reverse('api:management-owner-announcement-decision', args=[announcement.pk]),
            {
                'action': 'approve',
                'confirm_summary': True,
                'agreement_start_date': start_date.isoformat(),
                'agreement_end_date': end_date.isoformat(),
                'duration_months': months,
                'agreement_terms': 'One year advertising agreement.',
                'public_contact_visible': False,
            },
            format='json',
        )
        self.assertEqual(approval_response.status_code, 200, approval_response.data)

        public_response = self.client.get(reverse('api:property-list'))
        self.assertEqual(public_response.status_code, 200)
        public_property = next(
            item for item in public_response.data['results']
            if item['id'] == announcement.property_id
        )
        self.assertEqual(public_property['service_type'], Property.ServiceType.OWNER_ANNOUNCED)
        self.assertEqual(public_property['public_contact_phone'], '')

    def test_inactive_location_is_rejected_by_owner_submission(self):
        country = Location.objects.create(
            name='Test Country',
            slug='test-country',
            location_type=Location.Type.COUNTRY,
        )
        location = Location.objects.create(
            name='Inactive area',
            slug='inactive-area',
            location_type=Location.Type.CITY,
            parent=country,
            is_active=False,
        )
        self.client.force_authenticate(self.owner)
        payload = self.submission_payload()
        payload['administrative_location'] = location.pk
        response = self.client.post(
            reverse('api:owner-announcement-list'),
            payload,
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(OwnerAnnouncement.objects.exists())

    def test_expiry_command_sends_idempotent_reminders_and_expires_listing(self):
        announcement = self.submit_announcement()
        today = timezone.localdate()
        agreement = OwnerAnnouncementAgreement.objects.create(
            announcement=announcement,
            start_date=today,
            end_date=today + timedelta(days=7),
            duration_months=1,
            terms='One month agreement.',
            status=OwnerAnnouncementAgreement.Status.ACTIVE,
            approved_by=self.broker,
        )
        announcement.status = OwnerAnnouncement.Status.APPROVED
        announcement.save(update_fields=['status', 'updated_at'])

        command = Command()
        command.handle()
        command.handle()
        self.assertEqual(
            InAppNotification.objects.filter(
                recipient=self.owner,
                notification_type='agreement_expiry_reminder',
                announcement=announcement,
            ).count(),
            1,
        )

        agreement.start_date = today - timedelta(days=2)
        agreement.end_date = today - timedelta(days=1)
        agreement.save(update_fields=['start_date', 'end_date'])
        command.handle()
        self.assertEqual(
            agreement.__class__.objects.get(pk=agreement.pk).status,
            OwnerAnnouncementAgreement.Status.EXPIRED,
        )
        announcement.refresh_from_db()
        announcement.property.refresh_from_db()
        self.assertEqual(announcement.status, OwnerAnnouncement.Status.EXPIRED)
        self.assertEqual(
            announcement.property.publication_status,
            Property.PublicationStatus.EXPIRED,
        )
        self.assertEqual(
            OwnerAnnouncementEvent.objects.filter(
                announcement=announcement,
                event_type=OwnerAnnouncementEvent.Type.EXPIRED,
            ).count(),
            1,
        )

    def test_owner_cannot_read_another_users_announcement(self):
        announcement = self.submit_announcement()
        other_user = User.objects.create_user(
            username='another-owner',
            email='another-owner@example.test',
            password='secure-password-123',
        )
        self.client.force_authenticate(other_user)
        response = self.client.get(
            reverse('api:owner-announcement-detail', args=[announcement.pk]),
        )
        self.assertEqual(response.status_code, 404)

    def test_expired_announcement_can_be_renewed_and_republished_by_authorized_broker(self):
        announcement = self.submit_announcement()
        today = timezone.localdate()
        OwnerAnnouncementAgreement.objects.create(
            announcement=announcement,
            start_date=today - timedelta(days=31),
            end_date=today - timedelta(days=1),
            duration_months=1,
            terms='Expired advertising agreement.',
            status=OwnerAnnouncementAgreement.Status.EXPIRED,
            approved_by=self.broker,
        )
        announcement.status = OwnerAnnouncement.Status.EXPIRED
        announcement.property.publication_status = Property.PublicationStatus.EXPIRED
        announcement.property.save(update_fields=['publication_status', 'updated_at'])
        announcement.save(update_fields=['status', 'updated_at'])

        self.client.force_authenticate(self.owner)
        renewal_response = self.client.post(
            reverse('api:owner-announcement-renewal', args=[announcement.pk]),
        )
        self.assertEqual(renewal_response.status_code, 200, renewal_response.data)
        self.assertIsNotNone(renewal_response.data['renewal_requested_at'])

        start_date = today
        month_index = start_date.month
        year = start_date.year + month_index // 12
        month = month_index % 12 + 1
        end_date = date(year, month, min(start_date.day, monthrange(year, month)[1])) - timedelta(days=1)
        self.client.force_authenticate(self.broker)
        approval_response = self.client.post(
            reverse('api:management-owner-announcement-decision', args=[announcement.pk]),
            {
                'action': 'approve',
                'confirm_summary': True,
                'agreement_start_date': start_date.isoformat(),
                'agreement_end_date': end_date.isoformat(),
                'duration_months': 1,
                'agreement_terms': 'Renewed advertising agreement.',
                'public_contact_visible': False,
            },
            format='json',
        )
        self.assertEqual(approval_response.status_code, 200, approval_response.data)
        announcement.refresh_from_db()
        announcement.property.refresh_from_db()
        self.assertEqual(announcement.status, OwnerAnnouncement.Status.APPROVED)
        self.assertEqual(
            announcement.property.publication_status,
            Property.PublicationStatus.PUBLISHED,
        )
