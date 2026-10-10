from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Profile
from accounts.permissions import has_management_permission
from owner_announcements.models import (
    InAppNotification,
    OwnerAnnouncement,
    OwnerAnnouncementAgreement,
    OwnerAnnouncementEvent,
)
from properties.models import Property


REMINDER_DAYS = (30, 7, 1)
BROKER_REVIEW_PERMISSION = Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW


class Command(BaseCommand):
    help = 'Send idempotent in-app expiry reminders and expire ended owner listing agreements.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        agreements = OwnerAnnouncementAgreement.objects.filter(
            status=OwnerAnnouncementAgreement.Status.ACTIVE,
            announcement__status=OwnerAnnouncement.Status.APPROVED,
            start_date__lte=today,
        ).select_related('announcement__property', 'announcement__submitter')
        reminder_count = 0
        expired_count = 0

        for agreement in agreements.iterator():
            announcement = agreement.announcement
            if agreement.end_date < today:
                with transaction.atomic():
                    agreement.status = OwnerAnnouncementAgreement.Status.EXPIRED
                    agreement.save(update_fields=['status'])
                    previous_status = announcement.status
                    announcement.status = OwnerAnnouncement.Status.EXPIRED
                    announcement.reviewed_at = timezone.now()
                    announcement.save(update_fields=['status', 'reviewed_at', 'updated_at'])
                    announcement.property.publication_status = Property.PublicationStatus.EXPIRED
                    announcement.property.save(update_fields=['publication_status', 'updated_at'])
                    OwnerAnnouncementEvent.objects.create(
                        announcement=announcement,
                        event_type=OwnerAnnouncementEvent.Type.EXPIRED,
                        from_status=previous_status,
                        to_status=announcement.status,
                        details={'agreement_id': agreement.pk, 'agreement_end_date': agreement.end_date.isoformat()},
                    )
                    for recipient in self._recipients(announcement):
                        self._notify(
                            recipient,
                            announcement,
                            'announcement_expired',
                            f'The advertising agreement for {announcement.property.title} has expired.',
                            f'agreement:{agreement.pk}:expired:user:{recipient.pk}',
                        )
                    expired_count += 1
                continue

            remaining_days = (agreement.end_date - today).days
            if remaining_days not in REMINDER_DAYS:
                continue
            for recipient in self._recipients(announcement):
                _, created = self._notify(
                    recipient,
                    announcement,
                    'agreement_expiry_reminder',
                    f'The advertising agreement for {announcement.property.title} expires in {remaining_days} days.',
                    f'agreement:{agreement.pk}:expiry-reminder:{remaining_days}:user:{recipient.pk}',
                )
                reminder_count += int(created)

        self.stdout.write(self.style.SUCCESS(
            f'Created {reminder_count} expiry reminder(s); expired {expired_count} agreement(s).',
        ))

    def _recipients(self, announcement):
        recipients = {announcement.submitter_id: announcement.submitter}
        for profile in Profile.objects.select_related('user').filter(user__is_active=True):
            if has_management_permission(profile.user, BROKER_REVIEW_PERMISSION):
                recipients[profile.user_id] = profile.user
        return recipients.values()

    @staticmethod
    def _notify(recipient, announcement, notification_type, message, idempotency_key):
        return InAppNotification.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                'recipient': recipient,
                'announcement': announcement,
                'notification_type': notification_type,
                'message': message,
            },
        )
