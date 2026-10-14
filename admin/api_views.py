from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import Profile, TabSessionToken
from accounts.permissions import (
    HasManagementPermission,
    IsBrokerAccountManager,
    has_management_permission,
)
from accounts.serializers import (
    DelegatedAccountCreateSerializer,
    DelegatedAccountSerializer,
)
from admin.audit import record_admin_action
from admin.models import AdminAuditEvent, BrokerageSettings, HomepageNote
from admin.serializers import (
    AdminAuditEventSerializer,
    AdminBrokerAssignmentSerializer,
    AdminListingReportSerializer,
    AdminPropertySerializer,
    AdminUserSerializer,
    BrokerageSettingsSerializer,
    HomepageNoteSerializer,
    PublicBrokerageSettingsSerializer,
    PublicListingReportSerializer,
    PublicReportReceiptSerializer,
)
from properties.models import ListingReport, Property, PropertyBrokerAssignment


User = get_user_model()


class BrokerageSettingsView(APIView):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [BrokerageSettingsPermission()]

    def get_object(self):
        try:
            return BrokerageSettings.objects.get(pk=1)
        except BrokerageSettings.DoesNotExist:
            return BrokerageSettings(pk=1)

    @extend_schema(summary='Retrieve public site branding, brokerage contact, and social links')
    def get(self, request):
        serializer_class = (
            BrokerageSettingsSerializer
            if has_management_permission(request.user, Profile.Permission.SETTINGS_MANAGE)
            else PublicBrokerageSettingsSerializer
        )
        return Response(serializer_class(self.get_object(), context={'request': request}).data)

    @transaction.atomic
    @extend_schema(
        summary='Update site branding or authorized brokerage contact and social links',
        request=BrokerageSettingsSerializer,
        responses={200: BrokerageSettingsSerializer},
    )
    def patch(self, request):
        settings_obj, _ = BrokerageSettings.objects.select_for_update().get_or_create(pk=1)
        serializer = BrokerageSettingsSerializer(
            settings_obj,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        record_admin_action(
            request.user,
            action='brokerage_settings_updated',
            object_type='brokerage_settings',
            object_id=1,
            changes={'fields': list(serializer.validated_data)},
        )
        return Response(BrokerageSettingsSerializer(updated, context={'request': request}).data)


class BrokerageSettingsPermission(HasManagementPermission):
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        branding_fields = {'site_name', 'site_logo', 'clear_site_logo'}
        submitted_fields = set(request.data.keys())
        required_permissions = []
        if branding_fields.intersection(submitted_fields):
            required_permissions.append(Profile.Permission.BRANDING_MANAGE)
        if submitted_fields.difference(branding_fields):
            required_permissions.append(Profile.Permission.SETTINGS_MANAGE)
        if not required_permissions:
            required_permissions.append(Profile.Permission.SETTINGS_MANAGE)
        return all(
            has_management_permission(request.user, permission)
            for permission in required_permissions
        )


class PublicHomepageNoteListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = HomepageNoteSerializer
    queryset = HomepageNote.objects.filter(is_published=True).order_by('display_order', '-created_at')


class ManagedHomepageNoteListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.SETTINGS_MANAGE
    serializer_class = HomepageNoteSerializer
    queryset = HomepageNote.objects.all()

    @transaction.atomic
    def perform_create(self, serializer):
        note = serializer.save()
        record_admin_action(
            self.request.user,
            action='homepage_note_created',
            object_type='homepage_note',
            object_id=note.pk,
            changes={'is_published': note.is_published},
        )


class ManagedHomepageNoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.SETTINGS_MANAGE
    serializer_class = HomepageNoteSerializer
    queryset = HomepageNote.objects.all()
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    @transaction.atomic
    def perform_update(self, serializer):
        note = serializer.save()
        record_admin_action(
            self.request.user,
            action='homepage_note_updated',
            object_type='homepage_note',
            object_id=note.pk,
            changes={'fields': list(serializer.validated_data)},
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        record_admin_action(
            self.request.user,
            action='homepage_note_deleted',
            object_type='homepage_note',
            object_id=instance.pk,
            changes={'is_published': instance.is_published},
        )
        instance.delete()

class AdminUserListView(generics.ListAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.USERS_MANAGE
    serializer_class = AdminUserSerializer
    queryset = User.objects.none()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'profile__role', 'profile__broker_approved']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'username']
    ordering = ['-date_joined']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        return User.objects.filter(
            is_staff=False,
            is_superuser=False,
            profile__role=Profile.Role.BROKER,
        ).select_related('profile').order_by(*self.ordering)


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.USERS_MANAGE
    serializer_class = AdminUserSerializer
    queryset = User.objects.none()
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        return User.objects.filter(
            is_staff=False,
            is_superuser=False,
            profile__role=Profile.Role.BROKER,
        ).select_related('profile')

    @transaction.atomic
    def perform_update(self, serializer):
        user = serializer.instance
        before = {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'role': getattr(getattr(user, 'profile', None), 'role', None),
            'broker_approved': getattr(getattr(user, 'profile', None), 'broker_approved', False),
        }
        updated = serializer.save()
        profile = getattr(updated, 'profile', None)
        after = {
            'email': updated.email,
            'first_name': updated.first_name,
            'last_name': updated.last_name,
            'is_active': updated.is_active,
            'role': getattr(profile, 'role', None),
            'broker_approved': getattr(profile, 'broker_approved', False),
        }
        changes = {}
        for key, value in after.items():
            if before[key] == value:
                continue
            if key in {'email', 'first_name', 'last_name'}:
                changes[key] = 'updated'
            else:
                changes[key] = {'from': before[key], 'to': value}
        if changes:
            record_admin_action(
                self.request.user,
                action='user_updated',
                object_type='user',
                object_id=updated.pk,
                changes=changes,
            )

    @extend_schema(summary='View or update a customer, owner, or broker account')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class AdminDelegatedAccountListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsBrokerAccountManager]
    serializer_class = DelegatedAccountSerializer

    def get_queryset(self):
        return User.objects.filter(
            is_staff=False,
            is_superuser=False,
            profile__role=Profile.Role.BROKER,
        ).select_related('profile', 'profile__assigned_city').order_by('username')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = DelegatedAccountCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        profile = user.profile
        record_admin_action(
            request.user,
            action='broker_account_created',
            object_type='user',
            object_id=user.pk,
            changes={
                'role': profile.role,
                'assigned_city_id': profile.assigned_city_id,
                'management_permissions': profile.management_permissions,
                'is_active': user.is_active,
                'broker_onboarding_required': profile.broker_onboarding_required,
            },
        )
        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if request.method == 'POST':
            response['Cache-Control'] = 'no-store'
            response['Pragma'] = 'no-cache'
        return response


class AdminDelegatedAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsBrokerAccountManager]
    serializer_class = DelegatedAccountSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return User.objects.filter(
            is_staff=False,
            is_superuser=False,
            profile__role=Profile.Role.BROKER,
        ).select_related('profile', 'profile__assigned_city')

    @transaction.atomic
    def perform_update(self, serializer):
        user = serializer.instance
        before_profile = user.profile
        before = {
            'username': user.username,
            'contact_details': (
                user.email,
                user.first_name,
                user.last_name,
                before_profile.phone,
            ),
            'role': before_profile.role,
            'assigned_city_id': before_profile.assigned_city_id,
            'management_permissions': list(before_profile.management_permissions),
            'is_active': user.is_active,
            'broker_onboarding_required': before_profile.broker_onboarding_required,
            'broker_password_changed': before_profile.broker_password_changed,
        }
        updated = serializer.save()
        after_profile = updated.profile
        after = {
            'username': updated.username,
            'contact_details': (
                updated.email,
                updated.first_name,
                updated.last_name,
                after_profile.phone,
            ),
            'role': after_profile.role,
            'assigned_city_id': after_profile.assigned_city_id,
            'management_permissions': list(after_profile.management_permissions),
            'is_active': updated.is_active,
            'broker_onboarding_required': after_profile.broker_onboarding_required,
            'broker_password_changed': after_profile.broker_password_changed,
        }
        changes = {}
        if before['username'] != after['username']:
            changes['username'] = {'from': before['username'], 'to': after['username']}
        if before['contact_details'] != after['contact_details']:
            changes['contact_details_changed'] = True
        for key in (
            'role',
            'assigned_city_id',
            'management_permissions',
            'is_active',
            'broker_onboarding_required',
            'broker_password_changed',
        ):
            if before[key] != after[key]:
                changes[key] = {'from': before[key], 'to': after[key]}
        if changes:
            record_admin_action(
                self.request.user,
                action='broker_account_updated',
                object_type='user',
                object_id=updated.pk,
                changes=changes,
            )
        if (before['is_active'] and not updated.is_active) or self.request.data.get('initial_password'):
            TabSessionToken.objects.filter(
                user=updated,
                revoked_at__isnull=True,
            ).update(revoked_at=timezone.now())

    @transaction.atomic
    def perform_destroy(self, instance):
        record_admin_action(
            self.request.user,
            action='broker_account_deleted',
            object_type='user',
            object_id=instance.pk,
            changes={'username': instance.username},
        )
        instance.delete()


class AdminPropertyListView(generics.ListAPIView):
    permission_classes = [HasManagementPermission]
    permissions_by_method = {
        'GET': [
            Profile.Permission.PROPERTY_VIEW_ALL,
            Profile.Permission.PROPERTY_MODERATE,
        ],
    }
    serializer_class = AdminPropertySerializer
    queryset = Property.objects.none()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'publication_status', 'listing_type', 'property_type']
    search_fields = ['title', 'location', 'owner__username', 'submitted_by__username']
    ordering_fields = ['created_at', 'updated_at', 'price']
    ordering = ['-created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Property.objects.none()
        return Property.objects.filter(
            service_type=Property.ServiceType.BROKER_MANAGED,
        ).select_related('owner', 'submitted_by').order_by(*self.ordering)


class AdminPropertyDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [HasManagementPermission]
    permissions_by_method = {
        'GET': [
            Profile.Permission.PROPERTY_VIEW_ALL,
            Profile.Permission.PROPERTY_MODERATE,
        ],
        'PATCH': Profile.Permission.PROPERTY_MODERATE,
    }
    serializer_class = AdminPropertySerializer
    queryset = Property.objects.none()
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Property.objects.none()
        return Property.objects.filter(
            service_type=Property.ServiceType.BROKER_MANAGED,
        ).select_related('owner', 'submitted_by')

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        before = {
            'publication_status': instance.publication_status,
            'status': instance.status,
            'is_featured': instance.is_featured,
        }
        note = serializer.validated_data.pop('moderation_note', None)
        publication_status = serializer.validated_data.get(
            'publication_status',
            instance.publication_status,
        )
        if note is None:
            note = (
                instance.moderation_note
                if publication_status in (
                    Property.PublicationStatus.REJECTED,
                    Property.PublicationStatus.SUSPENDED,
                )
                else ''
            )
        updated = serializer.save(moderation_note=note)
        after = {
            'publication_status': updated.publication_status,
            'status': updated.status,
            'is_featured': updated.is_featured,
        }
        changes = {
            key: {'from': before[key], 'to': value}
            for key, value in after.items()
            if before[key] != value
        }
        if note:
            changes['moderation_note'] = note
        if changes:
            record_admin_action(
                self.request.user,
                action='property_moderated',
                object_type='property',
                object_id=updated.pk,
                changes=changes,
            )

    @extend_schema(summary='Inspect or moderate a property listing')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class AdminBrokerAssignmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.BROKERS_ASSIGN
    serializer_class = AdminBrokerAssignmentSerializer
    queryset = PropertyBrokerAssignment.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PropertyBrokerAssignment.objects.none()
        return PropertyBrokerAssignment.objects.filter(
            property_id=self.kwargs['property_id'],
            property__service_type=Property.ServiceType.BROKER_MANAGED,
        ).select_related('broker', 'granted_by')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        property_obj = get_object_or_404(
            Property.objects.select_for_update(),
            pk=self.kwargs['property_id'],
            service_type=Property.ServiceType.BROKER_MANAGED,
        )
        broker = serializer.validated_data['broker']
        assignment, created = PropertyBrokerAssignment.objects.get_or_create(
            property=property_obj,
            broker=broker,
            defaults={'granted_by': request.user},
        )
        serializer.instance = assignment
        if created:
            record_admin_action(
                request.user,
                action='broker_assigned',
                object_type='property',
                object_id=property_obj.pk,
                changes={'broker_id': broker.pk, 'broker_username': broker.get_username()},
            )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class AdminBrokerAssignmentDetailView(generics.DestroyAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.BROKERS_ASSIGN
    serializer_class = AdminBrokerAssignmentSerializer
    queryset = PropertyBrokerAssignment.objects.none()
    lookup_field = 'broker_id'
    lookup_url_kwarg = 'broker_id'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PropertyBrokerAssignment.objects.none()
        return PropertyBrokerAssignment.objects.filter(
            property_id=self.kwargs['property_id'],
            property__service_type=Property.ServiceType.BROKER_MANAGED,
        ).select_related('broker')

    @transaction.atomic
    def perform_destroy(self, instance):
        record_admin_action(
            self.request.user,
            action='broker_unassigned',
            object_type='property',
            object_id=instance.property_id,
            changes={'broker_id': instance.broker_id, 'broker_username': instance.broker.get_username()},
        )
        instance.delete()


class PublicListingReportCreateView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_listing_report'
    serializer_class = PublicListingReportSerializer

    @extend_schema(
        summary='Report a published property listing',
        responses={201: PublicReportReceiptSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(property_title=serializer.validated_data['property'].title)
        return Response(
            {'id': report.pk, 'status': report.status, 'created_at': report.created_at},
            status=status.HTTP_201_CREATED,
        )


class AdminListingReportListView(generics.ListAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.REPORTS_REVIEW
    serializer_class = AdminListingReportSerializer
    queryset = ListingReport.objects.none()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'reason']
    search_fields = ['property_title', 'reporter_name', 'reporter_email', 'details']
    ordering_fields = ['created_at', 'reviewed_at']
    ordering = ['-created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ListingReport.objects.none()
        return ListingReport.objects.select_related('property', 'reviewed_by').order_by(*self.ordering)


class AdminListingReportDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.REPORTS_REVIEW
    serializer_class = AdminListingReportSerializer
    queryset = ListingReport.objects.none()
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ListingReport.objects.none()
        return ListingReport.objects.select_related('property', 'reviewed_by')

    @transaction.atomic
    def perform_update(self, serializer):
        report = serializer.instance
        before_status = report.status
        before_notes = report.moderator_notes
        updated = serializer.save()
        changes = {}
        if updated.status != before_status:
            changes['status'] = {'from': before_status, 'to': updated.status}
        if updated.moderator_notes != before_notes:
            changes['moderator_notes'] = 'updated'
        if changes:
            record_admin_action(
                self.request.user,
                action='report_reviewed',
                object_type='listing_report',
                object_id=updated.pk,
                changes=changes,
            )

    @extend_schema(summary='Review or dismiss a submitted listing report')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class AdminAuditEventListView(generics.ListAPIView):
    permission_classes = [HasManagementPermission]
    required_management_permission = Profile.Permission.AUDIT_VIEW
    serializer_class = AdminAuditEventSerializer
    queryset = AdminAuditEvent.objects.none()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'object_type']
    search_fields = ['actor_username', 'object_id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AdminAuditEvent.objects.none()
        return AdminAuditEvent.objects.order_by(*self.ordering)

    @extend_schema(summary='List immutable administrator action records')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
