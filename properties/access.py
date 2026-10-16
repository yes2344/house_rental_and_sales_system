from django.db.models import Q
from django.utils import timezone

from accounts.models import Profile
from accounts.permissions import (
    has_management_permission,
    has_listing_role,
)
from properties.models import Location, Property


def broker_city_location_ids(user):
    profile = getattr(user, 'profile', None)
    city_id = getattr(profile, 'assigned_city_id', None)
    if city_id is None:
        return set()

    location_ids = {city_id}
    frontier = {city_id}
    while frontier:
        children = set(
            Location.objects.filter(parent_id__in=frontier)
            .values_list('pk', flat=True)
        )
        frontier = children - location_ids
        location_ids.update(frontier)
    return location_ids


def public_properties():
    return (
        Property.objects.filter(
            publication_status=Property.PublicationStatus.PUBLISHED,
            status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE],
        ).filter(
            Q(service_type=Property.ServiceType.BROKER_MANAGED)
            | Q(
                service_type=Property.ServiceType.OWNER_ANNOUNCED,
                owner_announcement__status='approved',
                owner_announcement__agreements__status='active',
                owner_announcement__agreements__start_date__lte=timezone.localdate(),
                owner_announcement__agreements__end_date__gte=timezone.localdate(),
            )
        ).distinct()
    )


def managed_properties(user):
    broker_managed = Property.objects.filter(service_type=Property.ServiceType.BROKER_MANAGED)
    if (
        has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        return broker_managed.filter(
            administrative_location_id__in=broker_city_location_ids(user),
        ).distinct()
    return Property.objects.none()


def editable_properties(user):
    broker_managed = Property.objects.filter(service_type=Property.ServiceType.BROKER_MANAGED)
    if (
        has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        return broker_managed.filter(
            administrative_location_id__in=broker_city_location_ids(user),
        ).distinct()
    return Property.objects.none()
