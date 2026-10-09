from django.db.models import Q

from accounts.models import Profile
from accounts.permissions import (
    has_management_permission,
    has_listing_role,
    is_platform_administrator,
)
from properties.models import Property


def managed_properties(user):
    if is_platform_administrator(user):
        return Property.objects.all()
    if has_management_permission(user, Profile.Permission.PROPERTY_VIEW_ALL) or has_management_permission(
        user,
        Profile.Permission.PROPERTY_MODERATE,
    ):
        return Property.objects.all()

    scope = Q()
    if has_listing_role(user, Profile.Role.OWNER):
        scope |= Q(owner=user)
    if user and user.is_authenticated:
        scope |= Q(submitted_by=user)
    if (
        has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        scope |= Q(assigned_brokers=user)
    return Property.objects.filter(scope).distinct() if scope else Property.objects.none()


def editable_properties(user):
    if is_platform_administrator(user):
        return Property.objects.all()
    if has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL):
        return Property.objects.all()

    scope = Q()
    if has_listing_role(user, Profile.Role.OWNER):
        scope |= Q(owner=user)
    if user and user.is_authenticated:
        scope |= Q(submitted_by=user)
    if (
        has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
        and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
    ):
        scope |= Q(assigned_brokers=user)
    return Property.objects.filter(scope).distinct() if scope else Property.objects.none()
