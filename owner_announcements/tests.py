from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Profile
from owner_announcements.models import (
    InAppNotification,
    OwnerAnnouncement,
    OwnerAnnouncementAgreement,
)
from properties.models import Location, Property


User = get_user_model()


class OwnerSubmissionWorkflowTests(APITestCase):
    def setUp(self):
        self.country = Location.objects.create(
            name='Ethiopia',
            slug='submission-ethiopia',
            location_type=Location.Type.COUNTRY,
        )
        self.city = Location.objects.create(
            name='Submission Test City',
            slug='submission-test-city',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        self.submitter = User.objects.create_user(
            username='submission-owner',
            email='owner@example.test',
            password='secure-password-123',
        )
        Profile.objects.create(
            user=self.submitter,
            role=Profile.Role.CUSTOMER,
        )
        self.other_user = User.objects.create_user(
            username='other-owner',
            email='other@example.test',
            password='secure-password-123',
        )
        Profile.objects.create(user=self.other_user, role=Profile.Role.CUSTOMER)
        self.agent = User.objects.create_user(
            username='submission-agent',
            email='agent@example.test',
            password='secure-password-123',
        )
        Profile.objects.create(
            user=self.agent,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=self.city,
            management_permissions=[
                Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED,
            ],
        )
        self.admin = User.objects.create_user(
            username='submission-admin',
            is_staff=True,
        )
        Profile.objects.create(
            user=self.admin,
            role=Profile.Role.ADMINISTRATOR,
        )
        self.submission_url = reverse('api:owner-submission-list')
        self.valid_payload = {
            'title': 'Owner-submitted family house',
            'location': 'Submission Test City',
            'administrative_location': self.city.pk,
            'category': 'house',
            'listing_type': 'sale',
            'price': '2500000.00',
            'bedrooms': 3,
            'bathrooms': 2,
            'area_value': '130',
            'area_unit': 'sqm',
            'rental_frequency': '',
            'description': 'A house submitted for review.',
            'features': 'Private garden',
            'amenities': [],
            'owner_contact_name': 'Private Owner',
            'owner_contact_phone': '+251900000001',
            'owner_contact_email': 'private-owner@example.test',
            'authorization_confirmed': True,
            'terms_accepted': True,
        }

    def submit(self):
        self.client.force_authenticate(self.submitter)
        response = self.client.post(self.submission_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def assign_to_agent(self, announcement):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse('api:owner-submission-assignment', args=[announcement.pk]),
            {'assigned_reviewer_id': self.agent.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(self.agent)
        return response

    def test_anonymous_submission_is_rejected(self):
        response = self.client.post(self.submission_url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Property.objects.count(), 0)

    def test_authenticated_submission_is_pending_private_and_audited(self):
        response = self.submit()
        property_obj = Property.objects.get(pk=response.data['id'])
        announcement = property_obj.owner_announcement

        self.assertEqual(property_obj.service_type, Property.ServiceType.OWNER_ANNOUNCED)
        self.assertEqual(property_obj.publication_status, Property.PublicationStatus.PENDING_REVIEW)
        self.assertEqual(property_obj.submitted_by_id, self.submitter.pk)
        self.assertEqual(response.data['owner_contact_name'], 'Private Owner')
        self.assertEqual(response.data['owner_contact_phone'], '+251900000001')
        self.assertEqual(response.data['owner_contact_email'], 'private-owner@example.test')
        self.assertEqual(announcement.status, OwnerAnnouncement.Status.PENDING_REVIEW)
        self.assertTrue(announcement.authorization_confirmed)
        self.assertEqual(announcement.events.count(), 1)
        self.assertEqual(announcement.notifications.count(), 1)
        public_list = self.client.get(reverse('api:property-list'))
        public_detail = self.client.get(reverse('api:property-detail', args=[property_obj.slug]))
        self.assertEqual(public_list.data['count'], 0)
        self.assertEqual(public_detail.status_code, 404)

    def test_cannot_set_publication_or_contact_fields_during_submission(self):
        self.client.force_authenticate(self.submitter)
        for field, value in (
            ('publication_status', 'published'),
            ('status', 'available'),
            ('service_type', 'broker_managed'),
            ('contact_phone', '+251900000009'),
        ):
            payload = {**self.valid_payload, field: value}
            with self.subTest(field=field):
                response = self.client.post(self.submission_url, payload, format='json')
                self.assertEqual(response.status_code, 400)
        self.assertEqual(Property.objects.count(), 0)

    def test_invalid_location_and_missing_consent_are_rejected(self):
        self.client.force_authenticate(self.submitter)
        invalid_location = self.client.post(
            self.submission_url,
            {**self.valid_payload, 'administrative_location': 999999},
            format='json',
        )
        missing_consent = self.client.post(
            self.submission_url,
            {**self.valid_payload, 'authorization_confirmed': False},
            format='json',
        )

        self.assertEqual(invalid_location.status_code, 400)
        self.assertEqual(missing_consent.status_code, 400)
        self.assertEqual(Property.objects.count(), 0)

    def test_city_administration_requires_a_configured_subcity(self):
        city_administration = Location.objects.create(
            name='Submission Test City Administration',
            slug='submission-test-city-administration',
            location_type=Location.Type.CITY_ADMINISTRATION,
            parent=self.country,
        )
        subcity = Location.objects.create(
            name='Submission Test Kifle Ketema',
            slug='submission-test-kifle-ketema',
            location_type=Location.Type.SUBCITY,
            parent=city_administration,
        )
        self.client.force_authenticate(self.submitter)

        missing_subcity = self.client.post(
            self.submission_url,
            {**self.valid_payload, 'administrative_location': city_administration.pk},
            format='json',
        )
        valid_subcity = self.client.post(
            self.submission_url,
            {**self.valid_payload, 'administrative_location': subcity.pk},
            format='json',
        )

        self.assertEqual(missing_subcity.status_code, 400)
        self.assertEqual(valid_subcity.status_code, 201, valid_subcity.data)

    def test_multiple_submissions_are_saved_independently(self):
        first = self.submit()
        second = self.client.post(
            self.submission_url,
            {**self.valid_payload, 'title': 'Another submitted property'},
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201, second.data)
        self.assertNotEqual(first.data['id'], second.data['id'])
        self.assertEqual(OwnerAnnouncement.objects.filter(submitter=self.submitter).count(), 2)

    def test_submitter_cannot_read_or_edit_another_users_submission(self):
        created = self.submit()
        self.client.force_authenticate(self.other_user)

        read = self.client.get(reverse('api:owner-submission-detail', args=[created.data['id']]))
        edit = self.client.patch(
            reverse('api:owner-submission-detail', args=[created.data['id']]),
            {'title': 'Changed by another user'},
            format='json',
        )

        self.assertEqual(read.status_code, 404)
        self.assertEqual(edit.status_code, 404)
        self.assertEqual(Property.objects.get(pk=created.data['id']).title, self.valid_payload['title'])

    def test_unauthorized_account_cannot_review_submissions(self):
        created = self.submit()
        announcement = OwnerAnnouncement.objects.get(property_id=created.data['id'])
        self.client.force_authenticate(self.other_user)

        response = self.client.get(reverse('api:owner-submission-review-list'))
        detail = self.client.get(
            reverse('api:owner-submission-review-detail', args=[announcement.pk]),
        )
        decision = self.client.post(
            reverse('api:owner-submission-review-decision', args=[announcement.pk]),
            {'action': 'reject', 'feedback': 'Unauthorized review attempt.'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(detail.status_code, 403)
        self.assertEqual(decision.status_code, 403)
        announcement.refresh_from_db()
        self.assertEqual(announcement.status, OwnerAnnouncement.Status.PENDING_REVIEW)

    def test_admin_queue_includes_every_submission_and_agent_queue_requires_assignment(self):
        created = self.submit()
        announcement = OwnerAnnouncement.objects.get(property_id=created.data['id'])

        self.client.force_authenticate(self.admin)
        admin_queue = self.client.get(reverse('api:owner-submission-review-list'))
        self.client.force_authenticate(self.agent)
        unassigned_agent_queue = self.client.get(reverse('api:owner-submission-review-list'))
        unassigned_detail = self.client.get(
            reverse('api:owner-submission-review-detail', args=[announcement.pk]),
        )

        self.assertEqual(admin_queue.status_code, 200)
        self.assertEqual(admin_queue.data['count'], 1)
        self.assertEqual(unassigned_agent_queue.status_code, 200)
        self.assertEqual(unassigned_agent_queue.data['count'], 0)
        self.assertEqual(unassigned_detail.status_code, 404)

        self.assign_to_agent(announcement)
        assigned_agent_queue = self.client.get(reverse('api:owner-submission-review-list'))
        self.client.force_authenticate(self.admin)
        admin_queue_after_assignment = self.client.get(
            reverse('api:owner-submission-review-list'),
        )

        self.assertEqual(assigned_agent_queue.data['count'], 1)
        self.assertEqual(admin_queue_after_assignment.data['count'], 1)

    def test_agent_without_explicit_review_permission_cannot_access_review_queue(self):
        unprivileged_agent = User.objects.create_user(username='unprivileged-agent')
        Profile.objects.create(
            user=unprivileged_agent,
            role=Profile.Role.BROKER,
            broker_approved=True,
            assigned_city=self.city,
        )
        self.client.force_authenticate(unprivileged_agent)

        response = self.client.get(reverse('api:owner-submission-review-list'))

        self.assertEqual(response.status_code, 403)

    def test_submitter_can_upload_images_but_another_user_cannot_access_them(self):
        created = self.submit()
        image_url = reverse('api:owner-submission-images', args=[created.data['id']])

        with TemporaryDirectory() as media_root, override_settings(
            MEDIA_ROOT=media_root,
            PRIVATE_MEDIA_ROOT=str(Path(media_root) / 'private'),
            CLOUDINARY_URL='',
        ):
            self.client.force_authenticate(self.submitter)
            uploaded = self.client.post(
                image_url,
                {
                    'image': SimpleUploadedFile(
                        'front.png',
                        self.make_submission_image(),
                        content_type='image/png',
                    ),
                },
                format='multipart',
            )
            self.client.force_authenticate(self.other_user)
            forbidden = self.client.get(image_url)

        self.assertEqual(uploaded.status_code, 201, uploaded.data)
        self.assertEqual(forbidden.status_code, 404)

    def make_submission_image(self):
        image_buffer = BytesIO()
        Image.new('RGB', (300, 200), color='white').save(image_buffer, format='PNG')
        return image_buffer.getvalue()

    def test_agent_can_request_corrections_and_submitter_can_resubmit(self):
        created = self.submit()
        announcement = OwnerAnnouncement.objects.get(property_id=created.data['id'])
        self.assign_to_agent(announcement)
        decision = self.client.post(
            reverse('api:owner-submission-review-decision', args=[announcement.pk]),
            {'action': 'request_corrections', 'feedback': 'Please update the property description.'},
            format='json',
        )
        self.assertEqual(decision.status_code, 200, decision.data)
        self.assertEqual(decision.data['status'], OwnerAnnouncement.Status.CORRECTIONS_REQUESTED)
        self.assertEqual(announcement.notifications.count(), 2)

        self.client.force_authenticate(self.submitter)
        protected_update = self.client.patch(
            reverse('api:owner-submission-detail', args=[created.data['id']]),
            {'publication_status': Property.PublicationStatus.PUBLISHED},
            format='json',
        )
        updated = self.client.patch(
            reverse('api:owner-submission-detail', args=[created.data['id']]),
            {'title': 'Updated property after review'},
            format='json',
        )

        self.assertEqual(protected_update.status_code, 400)
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data['submission_status'], OwnerAnnouncement.Status.PENDING_REVIEW)
        self.assertEqual(updated.data['title'], 'Updated property after review')

    def test_agent_cannot_approve_own_submission(self):
        created = self.submit()
        profile = self.submitter.profile
        profile.role = Profile.Role.BROKER
        profile.broker_approved = True
        profile.assigned_city = self.city
        profile.management_permissions = [
            Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED,
        ]
        profile.save()
        announcement = OwnerAnnouncement.objects.get(property_id=created.data['id'])
        announcement.assigned_reviewer = self.submitter
        announcement.save(update_fields=['assigned_reviewer'])
        self.client.force_authenticate(self.submitter)

        response = self.client.post(
            reverse('api:owner-submission-review-decision', args=[created.data['id']]),
            {'action': 'approve'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Property.objects.get(pk=created.data['id']).publication_status,
            Property.PublicationStatus.PENDING_REVIEW,
        )

    def test_agent_approval_requires_a_valid_agreement_and_publishes_safely(self):
        created = self.submit()
        announcement = OwnerAnnouncement.objects.get(property_id=created.data['id'])
        self.assign_to_agent(announcement)
        decision_url = reverse('api:owner-submission-review-decision', args=[announcement.pk])
        missing_agreement = self.client.post(decision_url, {'action': 'approve'}, format='json')
        self.assertEqual(missing_agreement.status_code, 400)
        self.assertEqual(
            Property.objects.get(pk=created.data['id']).publication_status,
            Property.PublicationStatus.PENDING_REVIEW,
        )

        response = self.client.post(
            decision_url,
            {
                'action': 'approve',
                'agreement_start_date': timezone.localdate().isoformat(),
                'agreement_duration_months': 12,
                'agreement_terms': 'The platform will manage contact and listing inquiries.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        announcement.refresh_from_db()
        property_obj = Property.objects.get(pk=created.data['id'])
        agreement = OwnerAnnouncementAgreement.objects.get(announcement=announcement)
        self.assertEqual(announcement.status, OwnerAnnouncement.Status.APPROVED)
        self.assertEqual(property_obj.publication_status, Property.PublicationStatus.PUBLISHED)
        self.assertFalse(agreement.public_contact_visible)
        self.assertFalse(property_obj.contact_publicly_visible)
        self.assertEqual(announcement.notifications.count(), 2)
        public_list = self.client.get(reverse('api:property-list'))
        self.assertEqual(public_list.data['count'], 1)
        public_property = public_list.data['results'][0]
        self.assertEqual(public_property['id'], property_obj.pk)
        self.assertEqual(public_property['public_contact_name'], '')
        self.assertEqual(public_property['public_contact_phone'], '')
        self.assertEqual(public_property['public_contact_email'], '')

    def test_agent_rejection_requires_explanation_and_keeps_property_hidden(self):
        created = self.submit()
        announcement = OwnerAnnouncement.objects.get(property_id=created.data['id'])
        self.assign_to_agent(announcement)
        decision_url = reverse('api:owner-submission-review-decision', args=[announcement.pk])
        missing_reason = self.client.post(decision_url, {'action': 'reject'}, format='json')
        rejected = self.client.post(
            decision_url,
            {'action': 'reject', 'feedback': 'The submission details could not be verified.'},
            format='json',
        )
        property_obj = Property.objects.get(pk=created.data['id'])
        public_detail = self.client.get(reverse('api:property-detail', args=[property_obj.slug]))

        self.assertEqual(missing_reason.status_code, 400)
        self.assertEqual(rejected.status_code, 200, rejected.data)
        announcement.refresh_from_db()
        self.assertEqual(property_obj.publication_status, Property.PublicationStatus.REJECTED)
        self.assertEqual(announcement.status, OwnerAnnouncement.Status.REJECTED)
        self.assertEqual(public_detail.status_code, 404)

    def test_agent_review_scope_follows_assignment_not_city(self):
        foreign_city = Location.objects.create(
            name='Foreign Submission City',
            slug='foreign-submission-city',
            location_type=Location.Type.CITY,
            parent=self.country,
        )
        self.client.force_authenticate(self.submitter)
        foreign = self.client.post(
            self.submission_url,
            {**self.valid_payload, 'administrative_location': foreign_city.pk},
            format='json',
        )
        self.assertEqual(foreign.status_code, 201, foreign.data)
        announcement = OwnerAnnouncement.objects.get(property_id=foreign.data['id'])
        self.assign_to_agent(announcement)
        response = self.client.get(reverse('api:owner-submission-review-list'))
        foreign_detail = self.client.get(
            reverse('api:owner-submission-review-detail', args=[announcement.pk]),
        )
        local_submission = self.submit()
        local_announcement = OwnerAnnouncement.objects.get(
            property_id=local_submission.data['id'],
        )
        self.client.force_authenticate(self.agent)
        unassigned_detail = self.client.get(
            reverse('api:owner-submission-review-detail', args=[local_announcement.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(foreign_detail.status_code, 200)
        self.assertEqual(unassigned_detail.status_code, 404)

    def test_historical_owner_announcements_are_retained_but_not_public(self):
        legacy_property = Property.objects.create(
            title='Historical owner listing',
            location='Recorded location',
            property_type='house',
            listing_type=Property.ListingType.SALE,
            price='2500000.00',
            description='Historical record retained for audit purposes.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
            service_type=Property.ServiceType.OWNER_ANNOUNCED,
            submitted_by=self.submitter,
        )
        announcement = OwnerAnnouncement.objects.create(
            property=legacy_property,
            submitter=self.submitter,
            owner_contact_name='Legacy Owner',
            owner_contact_phone='+251900000002',
            authorization_confirmed=True,
            terms_accepted_at=timezone.now(),
        )

        public_list = self.client.get(reverse('api:property-list'))
        public_detail = self.client.get(
            reverse('api:property-detail', args=[legacy_property.slug]),
        )

        self.assertEqual(public_list.status_code, 200)
        self.assertNotIn(
            legacy_property.pk,
            {item['id'] for item in public_list.data['results']},
        )
        self.assertEqual(public_detail.status_code, 404)
        self.assertTrue(Property.objects.filter(pk=legacy_property.pk).exists())
        self.assertTrue(OwnerAnnouncement.objects.filter(pk=announcement.pk).exists())

    def test_shared_notification_list_and_read_endpoints_remain_available(self):
        self.submit()
        self.client.force_authenticate(self.submitter)

        response = self.client.get(reverse('api:notification-list'))
        self.assertEqual(response.status_code, 200)
        notification_id = response.data['results'][0]['id']

        read_response = self.client.post(
            reverse('api:notification-read', args=[notification_id]),
        )
        self.assertEqual(read_response.status_code, 200)
        notification = InAppNotification.objects.get(pk=notification_id)
        self.assertIsNotNone(notification.read_at)
