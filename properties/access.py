from django.db.models import Q
from django.utils import timezone

from accounts.models import Profile
from accounts.permissions import (
    has_management_permission,
    has_listing_role,
)
from properties.models import Location, Property


def agent_city_location_ids(user):
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
            Q(service_type=Property.ServiceType.AGENT_MANAGED)
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
    agent_managed = Property.objects.filter(service_type=Property.ServiceType.AGENT_MANAGED)
    if any(
        has_management_permission(user, permission)
        for permission in (
            Profile.Permission.PROPERTY_VIEW_ALL,
            Profile.Permission.PROPERTY_MODERATE,
            Profile.Permission.PROPERTY_EDIT_ALL,
            Profile.Permission.PROPERTY_DELETE_ALL,
        )
    ):
        return agent_managed
    if (
        has_listing_role(user, Profile.Role.AGENT, agent_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        return agent_managed.filter(submitted_by=user)
    return Property.objects.none()


def editable_properties(user):
    agent_managed = Property.objects.filter(service_type=Property.ServiceType.AGENT_MANAGED)
    if has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL):
        return agent_managed
    if (
        has_listing_role(user, Profile.Role.AGENT, agent_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        return agent_managed.filter(submitted_by=user)
    return Property.objects.none()


def can_access_property_image_original(user, property_obj):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if any(
        has_management_permission(user, permission)
        for permission in (
            Profile.Permission.PROPERTY_VIEW_ALL,
            Profile.Permission.PROPERTY_EDIT_ALL,
        )
    ):
        return True
    if (
        property_obj.submitted_by_id == user.pk
        and has_listing_role(user, Profile.Role.AGENT, agent_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        return True
    return bool(
        property_obj.service_type == Property.ServiceType.OWNER_ANNOUNCED
        and getattr(property_obj, 'owner_announcement', None)
        and property_obj.owner_announcement.submitter_id == user.pk
    )
