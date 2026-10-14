from rest_framework.permissions import BasePermission

from accounts.models import Profile
from properties.models import Location


ADMIN_MANAGEMENT_PERMISSIONS = frozenset({
    Profile.Permission.BRANDING_MANAGE,
    Profile.Permission.LOCATIONS_MANAGE_CITIES,
    Profile.Permission.STAFF_MANAGE,
})
BROKER_WORK_PERMISSIONS = frozenset({
    Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
    Profile.Permission.VIEWING_MANAGE_ASSIGNED,
    Profile.Permission.LOCATIONS_MANAGE_SUBCITIES,
})


def broker_work_permissions():
    return [
        permission
        for permission, _ in Profile.Permission.choices
        if permission in BROKER_WORK_PERMISSIONS
    ]


def effective_management_permissions(user):
    if user.is_superuser:
        permissions = [
            permission
            for permission, _ in Profile.Permission.choices
            if user.is_active and permission in ADMIN_MANAGEMENT_PERMISSIONS
        ]
        return permissions
    profile = getattr(user, 'profile', None)
    if profile is None:
        return []
    if profile.role == Profile.Role.ADMINISTRATOR:
        return [
            permission
            for permission, _ in Profile.Permission.choices
            if user.is_staff and permission in ADMIN_MANAGEMENT_PERMISSIONS
        ]
    if profile.role == Profile.Role.BROKER and profile.broker_approved:
        return broker_work_permissions()
    return []


def has_management_permission(user, permission):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return permission in ADMIN_MANAGEMENT_PERMISSIONS
    profile = Profile.objects.filter(user_id=user.pk).first()
    if profile is None:
        return False
    if profile.role == Profile.Role.ADMINISTRATOR:
        return bool(user.is_staff and permission in ADMIN_MANAGEMENT_PERMISSIONS)
    if profile.role == Profile.Role.BROKER:
        return profile.broker_approved and permission in BROKER_WORK_PERMISSIONS
    return False


def can_manage_broker_accounts(user):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return bool(
        user.is_staff
        and Profile.objects.filter(
            user_id=user.pk,
            role=Profile.Role.ADMINISTRATOR,
        ).exists()
    )


class IsBrokerAccountManager(BasePermission):
    def has_permission(self, request, view):
        return can_manage_broker_accounts(request.user)


class IsLocationManager(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            has_management_permission(user, Profile.Permission.LOCATIONS_MANAGE_CITIES)
            or has_management_permission(user, Profile.Permission.LOCATIONS_MANAGE_SUBCITIES)
        )


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


class IsActiveAuthenticated(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)


class IsNotBrokerAccount(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not Profile.objects.filter(user_id=user.pk, role=Profile.Role.BROKER).exists()
        )


class IsListingManager(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return any(
            has_management_permission(user, permission)
            for permission in (
                Profile.Permission.PROPERTY_VIEW_ALL,
                Profile.Permission.PROPERTY_MODERATE,
                Profile.Permission.PROPERTY_EDIT_ALL,
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
            )
        )


class IsPropertyManagerOrAdministrator(IsListingManager):
    def has_object_permission(self, request, view, obj):
        user = request.user
        property_obj = getattr(obj, 'property', obj)
        assigned_broker = (
            has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
            and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
            and property_obj.assigned_brokers.filter(pk=user.pk).exists()
        )
        profile = Profile.objects.filter(
            user=user,
            role=Profile.Role.BROKER,
            broker_approved=True,
        ).select_related('assigned_city').first()
        property_city_id = None
        location = property_obj.administrative_location
        while location is not None:
            if location.location_type == Location.Type.CITY:
                property_city_id = location.pk
                break
            location = location.parent
        city_broker = bool(
            profile
            and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
            and profile.assigned_city_id
            and property_city_id == profile.assigned_city_id
        )
        if assigned_broker or city_broker:
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
            return (
                has_management_permission(user, Profile.Permission.PROPERTY_DELETE_ALL)
                or has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL)
                or assigned_broker
            )
        return has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL) or assigned_broker or city_broker


class IsAuthenticatedPropertyManagerOrAdministrator(IsPropertyManagerOrAdministrator):
    def has_permission(self, request, view):
        user = request.user
        if not super().has_permission(request, view):
            return False
        if request.method == 'POST':
            can_create_globally = (
                has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL)
                and has_management_permission(user, Profile.Permission.PROPERTY_MODERATE)
            )
            can_create_as_broker = (
                has_listing_role(user, Profile.Role.BROKER, broker_approved=True)
                and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
                and bool(getattr(getattr(user, 'profile', None), 'assigned_city_id', None))
            )
            return can_create_globally or can_create_as_broker
        return True


class IsViewingRequestManager(IsPropertyManagerOrAdministrator):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return any(
            has_management_permission(user, permission)
            for permission in (
                Profile.Permission.VIEWING_VIEW_ALL,
                Profile.Permission.VIEWING_MANAGE_ALL,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            )
        )

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
        return False
