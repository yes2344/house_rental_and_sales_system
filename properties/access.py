from django.db.models import Q

from accounts.models import Profile
from accounts.permissions import (
    has_management_permission,
    has_listing_role,
)
from properties.models import Property


def public_properties():
    return (
        Property.objects.filter(
            publication_status=Property.PublicationStatus.PUBLISHED,
            status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE],
            service_type=Property.ServiceType.BROKER_MANAGED,
        )
    )


def managed_properties(user):
    broker_managed = Property.objects.filter(service_type=Property.ServiceType.BROKER_MANAGED)
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
    if has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL):
        return broker_managed

    scope = Q(pk__in=[])
    if (
        has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        scope |= Q(assigned_brokers=user, service_type=Property.ServiceType.BROKER_MANAGED)
    return broker_managed.filter(scope).distinct() if scope else Property.objects.none()
