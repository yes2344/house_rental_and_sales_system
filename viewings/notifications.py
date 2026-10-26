from owner_announcements.models import InAppNotification
from accounts.models import Profile
from accounts.permissions import can_manage_published_property_viewings


def notify_viewing_request_event(viewing_request, event, *, to_requester):
    recipients = []
    if to_requester:
        if viewing_request.requester_id:
            recipients.append(viewing_request.requester)
    else:
        recipients.extend(
            profile.user
            for profile in Profile.objects.filter(
                role=Profile.Role.AGENT,
                agent_approved=True,
                user__is_active=True,
            ).select_related('user')
        )
        publisher = viewing_request.property.submitted_by
        if (
            publisher is not None
            and can_manage_published_property_viewings(publisher, viewing_request.property)
        ):
            recipients.append(publisher)

    if not recipients:
        return

    message = (
        f'Viewing request for {viewing_request.property.title}: '
        f'{event.get_event_type_display()}.'
    )[:500]
    for recipient in recipients:
        InAppNotification.objects.get_or_create(
            idempotency_key=(
                f'viewing:{viewing_request.pk}:event:{event.pk}:recipient:{recipient.pk}'
            ),
            defaults={
                'recipient': recipient,
                'notification_type': 'viewing_request_updated',
                'message': message,
            },
        )
