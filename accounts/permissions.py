from rest_framework.permissions import BasePermission

from accounts.models import Profile


def is_platform_administrator(user):
    return bool(user and user.is_authenticated and user.is_active and user.is_superuser)


def has_management_permission(user, permission):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    profile = Profile.objects.filter(user_id=user.pk).first()
    if profile is None or permission not in profile.management_permissions:
        return False
    if profile.role == Profile.Role.ADMINISTRATOR:
        return bool(user.is_staff)
    if profile.role == Profile.Role.BROKER:
        return profile.broker_approved
    return False


class IsPlatformOwner(BasePermission):
    def has_permission(self, request, view):
        return is_platform_administrator(request.user)


class HasManagementPermission(BasePermission):
    def has_permission(self, request, view):
        permissions_by_method = getattr(view, 'permissions_by_method', {})
        required_permission = permissions_by_method.get(
            request.method,
            permissions_by_method.get('GET') if request.method in ('HEAD', 'OPTIONS') else None,
        )
        if required_permission is None:
            required_permission = getattr(view, 'required_management_permission', None)
        if isinstance(required_permission, (list, tuple, set)):
            return any(
                has_management_permission(request.user, permission)
                for permission in required_permission
            )
        return bool(required_permission and has_management_permission(request.user, required_permission))


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


class IsActiveAuthenticated(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)


class IsListingManager(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            is_platform_administrator(user)
            or has_listing_role(user, Profile.Role.OWNER)
            or (
                has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
                and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
            )
        )


class IsPropertyManagerOrAdministrator(IsListingManager):
    def has_object_permission(self, request, view, obj):
        user = request.user
        property_obj = getattr(obj, 'property', obj)
        if is_platform_administrator(user):
            return True
        if has_listing_role(user, Profile.Role.OWNER) and property_obj.owner_id == user.pk:
            return True
        if property_obj.submitted_by_id == user.pk:
            return True
        assigned_broker = (
            has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
            and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
            and property_obj.assigned_brokers.filter(pk=user.pk).exists()
        )
        if assigned_broker:
            return True

        request_method = getattr(request, 'method', 'GET')
        if request_method in ('GET', 'HEAD', 'OPTIONS'):
            return any(
                has_management_permission(user, permission)
                for permission in (
                    Profile.Permission.PROPERTY_VIEW_ALL,
                    Profile.Permission.PROPERTY_MODERATE,
                    Profile.Permission.PROPERTY_EDIT_ALL,
                )
            )
        if request_method == 'DELETE':
            return has_management_permission(user, Profile.Permission.PROPERTY_DELETE_ALL)
        return has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL)


class IsAuthenticatedPropertyManagerOrAdministrator(IsPropertyManagerOrAdministrator):
    def has_permission(self, request, view):
        user = request.user
        return is_platform_administrator(user) or bool(
            user and user.is_authenticated and user.is_active
        )


class IsViewingRequestManager(IsPropertyManagerOrAdministrator):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if is_platform_administrator(user):
            return True
        if has_listing_role(user, Profile.Role.OWNER):
            return True
        if has_listing_role(user, Profile.Role.BROKER, broker_approved=True):
            return any(
                has_management_permission(user, permission)
                for permission in (
                    Profile.Permission.VIEWING_VIEW_ALL,
                    Profile.Permission.VIEWING_MANAGE_ALL,
                    Profile.Permission.VIEWING_MANAGE_ASSIGNED,
                )
            )
        if any(
            has_management_permission(user, permission)
            for permission in (
                Profile.Permission.VIEWING_VIEW_ALL,
                Profile.Permission.VIEWING_MANAGE_ALL,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            )
        ):
            return True
        from properties.models import Property

        return Property.objects.filter(submitted_by=user).exists()

    def has_object_permission(self, request, view, obj):
        request_method = getattr(request, 'method', 'GET')
        is_read = request_method in ('GET', 'HEAD', 'OPTIONS')
        if is_read and has_management_permission(
            request.user,
            Profile.Permission.VIEWING_VIEW_ALL,
        ):
            return True
        if has_management_permission(request.user, Profile.Permission.VIEWING_MANAGE_ALL):
            return True
        if (
            has_management_permission(request.user, Profile.Permission.VIEWING_MANAGE_ASSIGNED)
            and obj.property.assigned_brokers.filter(pk=request.user.pk).exists()
        ):
            return True
        if has_listing_role(request.user, Profile.Role.OWNER):
            return obj.property.owner_id == request.user.pk
        return obj.property.submitted_by_id == request.user.pk
