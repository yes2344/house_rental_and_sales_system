from django.apps import apps
from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

from accounts.models import Profile


ADMIN_MANAGEMENT_PERMISSIONS = frozenset({
    Profile.Permission.PROPERTY_VIEW_ALL,
    Profile.Permission.PROPERTY_MODERATE,
    Profile.Permission.PROPERTY_EDIT_ALL,
    Profile.Permission.PROPERTY_DELETE_ALL,
    Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
    Profile.Permission.BRANDING_MANAGE,
    Profile.Permission.LOCATIONS_MANAGE_CITIES,
    Profile.Permission.STAFF_MANAGE,
    Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW,
    Profile.Permission.OWNER_ANNOUNCEMENTS_ASSIGN,
})
AGENT_WORK_PERMISSIONS = frozenset({
    Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
    Profile.Permission.VIEWING_MANAGE_ASSIGNED,
    Profile.Permission.LOCATIONS_MANAGE_SUBCITIES,
})
AGENT_GRANTABLE_PERMISSIONS = frozenset({
    Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW_ASSIGNED,
})


def agent_work_permissions():
    return [
        permission
        for permission, _ in Profile.Permission.choices
        if permission in AGENT_WORK_PERMISSIONS
    ]


def agent_grantable_permissions():
    return list(AGENT_GRANTABLE_PERMISSIONS)


def is_platform_owner(user):
    if not user or not user.is_authenticated or not user.is_active or not user.is_superuser:
        return False
    settings_model = apps.get_model('portal_admin', 'BrokerageSettings')
    owner_id = settings_model.objects.filter(pk=1).values_list('platform_owner_id', flat=True).first()
    if owner_id is not None and get_user_model().objects.filter(
        pk=owner_id,
        is_superuser=True,
        is_active=True,
    ).exists():
        return owner_id == user.pk
    else:
        owner_id = get_user_model().objects.filter(
            is_superuser=True,
            is_active=True,
        ).order_by('pk').values_list('pk', flat=True).first()
    return owner_id == user.pk


def effective_management_permissions(user):
    if user.is_superuser:
        permissions = [
            permission
            for permission, _ in Profile.Permission.choices
            if user.is_active and (
                permission in ADMIN_MANAGEMENT_PERMISSIONS
                or (
                    permission == Profile.Permission.SETTINGS_MANAGE
                    and is_platform_owner(user)
                )
            )
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
    if profile.role == Profile.Role.AGENT and profile.agent_approved:
        permissions = agent_work_permissions()
        permissions.extend(
            permission
            for permission in AGENT_GRANTABLE_PERMISSIONS
            if permission in profile.management_permissions
        )
        if Profile.Permission.SETTINGS_MANAGE in profile.management_permissions:
            permissions.append(Profile.Permission.SETTINGS_MANAGE)
        return permissions
    return []


def has_management_permission(user, permission):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return (
            permission in ADMIN_MANAGEMENT_PERMISSIONS
            or (
                permission == Profile.Permission.SETTINGS_MANAGE
                and is_platform_owner(user)
            )
        )
    profile = Profile.objects.filter(user_id=user.pk).first()
    if profile is None:
        return False
    if profile.role == Profile.Role.ADMINISTRATOR:
        return bool(user.is_staff and permission in ADMIN_MANAGEMENT_PERMISSIONS)
    if profile.role == Profile.Role.AGENT:
        if not profile.agent_approved:
            return False
        return (
            permission in AGENT_WORK_PERMISSIONS
            or (
                permission in AGENT_GRANTABLE_PERMISSIONS
                and permission in profile.management_permissions
            )
            or (
                permission == Profile.Permission.SETTINGS_MANAGE
                and permission in profile.management_permissions
            )
        )
    return False


def can_manage_published_property_viewings(user, property_obj=None):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    is_administrator = user.is_superuser or Profile.objects.filter(
        user_id=user.pk,
        role=Profile.Role.ADMINISTRATOR,
    ).exists()
    if not is_administrator:
        return False
    property_model = apps.get_model('properties', 'Property')
    if property_obj is None:
        if not property_model.objects.filter(submitted_by_id=user.pk).exists():
            return False
    elif property_obj.submitted_by_id != user.pk:
        return False
    return any(
        has_management_permission(user, permission)
        for permission in (
            Profile.Permission.PROPERTY_VIEW_ALL,
            Profile.Permission.PROPERTY_MODERATE,
            Profile.Permission.PROPERTY_EDIT_ALL,
            Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
        )
    )


def can_manage_agent_accounts(user):
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


class IsAgentAccountManager(BasePermission):
    def has_permission(self, request, view):
        return can_manage_agent_accounts(request.user)


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


def has_listing_role(user, role, *, agent_approved=False):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    filters = {'user_id': user.pk, 'role': role}
    if role == Profile.Role.AGENT:
        filters['agent_approved'] = agent_approved
    return Profile.objects.filter(**filters).exists()


class IsActiveAuthenticated(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)


class IsNotAgentAccount(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not Profile.objects.filter(user_id=user.pk, role=Profile.Role.AGENT).exists()
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
        owns_agent_listing = (
            has_listing_role(user, Profile.Role.AGENT, agent_approved=True)
            and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
            and property_obj.submitted_by_id == user.pk
        )
        if owns_agent_listing:
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
            )
        return has_management_permission(user, Profile.Permission.PROPERTY_EDIT_ALL)


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
            can_create_as_agent = (
                has_listing_role(user, Profile.Role.AGENT, agent_approved=True)
                and has_management_permission(user, Profile.Permission.PROPERTY_MANAGE_ASSIGNED)
                and bool(getattr(getattr(user, 'profile', None), 'assigned_city_id', None))
            )
            return can_create_globally or can_create_as_agent
        return True


class IsViewingRequestManager(IsPropertyManagerOrAdministrator):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return can_manage_published_property_viewings(user) or any(
            has_management_permission(user, permission)
            for permission in (
                Profile.Permission.VIEWING_VIEW_ALL,
                Profile.Permission.VIEWING_MANAGE_ALL,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            )
        )

    def has_object_permission(self, request, view, obj):
        if can_manage_published_property_viewings(request.user, obj.property):
            return True
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
            and obj.property.assigned_agents.filter(pk=request.user.pk).exists()
        ):
            return True
        return False
