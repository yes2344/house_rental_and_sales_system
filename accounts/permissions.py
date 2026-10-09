from rest_framework.permissions import BasePermission

from accounts.models import Profile


def is_platform_administrator(user):
    return bool(user and user.is_authenticated and user.is_active and user.is_staff)


def has_listing_role(user, role, *, broker_approved=False):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    filters = {'user_id': user.pk, 'role': role}
    if role == Profile.Role.BROKER:
        filters['broker_approved'] = broker_approved
    return Profile.objects.filter(**filters).exists()


class IsPlatformAdministrator(BasePermission):
    def has_permission(self, request, view):
        return is_platform_administrator(request.user)


class IsListingManager(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            is_platform_administrator(user)
            or has_listing_role(user, Profile.Role.OWNER)
            or has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
        )


class IsPropertyManagerOrAdministrator(IsListingManager):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_platform_administrator(user):
            return True
        if has_listing_role(user, Profile.Role.OWNER) and obj.owner_id == user.pk:
            return True
        return (
            has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
            and obj.assigned_brokers.filter(pk=user.pk).exists()
        )


class IsViewingRequestManager(IsPropertyManagerOrAdministrator):
    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(request, view, obj.property)
