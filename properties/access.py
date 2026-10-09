from django.db.models import Q

from accounts.models import Profile
from accounts.permissions import has_listing_role, is_platform_administrator
from properties.models import Property


def managed_properties(user):
    if is_platform_administrator(user):
        return Property.objects.all()

    scope = Q()
    if has_listing_role(user, Profile.Role.OWNER):
        scope |= Q(owner=user)
    if has_listing_role(user, Profile.Role.BROKER, broker_approved=True):
        scope |= Q(assigned_brokers=user)
    return Property.objects.filter(scope).distinct() if scope else Property.objects.none()
