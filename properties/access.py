from django.db.models import Q
from django.utils import timezone

from accounts.models import Profile
from accounts.permissions import (
    has_management_permission,
    has_listing_role,
    is_platform_administrator,
)
from properties.models import Property
from owner_announcements.models import OwnerAnnouncement, OwnerAnnouncementAgreement


def public_properties():
    today = timezone.localdate()
    owner_scope = Q(
        service_type=Property.ServiceType.OWNER_ANNOUNCED,
        owner_announcement__status=OwnerAnnouncement.Status.APPROVED,
        owner_announcement__agreements__status=OwnerAnnouncementAgreement.Status.ACTIVE,
        owner_announcement__agreements__start_date__lte=today,
        owner_announcement__agreements__end_date__gte=today,
    )
    return (
        Property.objects.filter(
            publication_status=Property.PublicationStatus.PUBLISHED,
            status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE],
        )
        .filter(Q(service_type=Property.ServiceType.BROKER_MANAGED) | owner_scope)
        .distinct()
    )


def managed_properties(user):
    broker_managed = Property.objects.filter(service_type=Property.ServiceType.BROKER_MANAGED)
    if is_platform_administrator(user):
        return broker_managed
    if has_management_permission(user, Profile.Permission.PROPERTY_VIEW_ALL) or has_management_permission(
        user,
        Profile.Permission.PROPERTY_MODERATE,
    ):
        return broker_managed

    scope = Q(pk__in=[])
    if (
        has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        scope |= Q(assigned_brokers=user, service_type=Property.ServiceType.BROKER_MANAGED)
    return broker_managed.filter(scope).distinct() if scope else Property.objects.none()


def editable_properties(user):
    broker_managed = Property.objects.filter(service_type=Property.ServiceType.BROKER_MANAGED)
    if is_platform_administrator(user):
        return broker_managed
    if has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL):
        return broker_managed

    scope = Q(pk__in=[])
    if (
        has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        scope |= Q(assigned_brokers=user, service_type=Property.ServiceType.BROKER_MANAGED)
    return broker_managed.filter(scope).distinct() if scope else Property.objects.none()
