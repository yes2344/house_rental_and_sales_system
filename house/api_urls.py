from django.urls import path

from admin.api_views import (
    AdminAuditEventListView,
    AdminBrokerAssignmentDetailView,
    AdminBrokerAssignmentListCreateView,
    AdminDelegatedAccountDetailView,
    AdminDelegatedAccountListCreateView,
    AdminListingReportDetailView,
    AdminListingReportListView,
    AdminPropertyDetailView,
    AdminPropertyListView,
    AdminUserDetailView,
    AdminUserListView,
    PublicListingReportCreateView,
)
from accounts.api_views import (
    AccountPreferencesResetView,
    AccountPreferencesView,
    AccountActivityView,
    AccountMeView,
    CsrfTokenView,
    DelegatedInvitationAcceptView,
    LoginView,
    LogoutView,
    RegistrationView,
)
from favorites.views import FavoriteDeleteView, FavoriteListCreateView
from properties.views import (
    ManagedPropertyDetailView,
    ManagedPropertyImageDetailView,
    ManagedPropertyImageListCreateView,
    ManagedPropertyListCreateView,
    ManagedPropertySubmitView,
    PublicAmenityListView,
    PublicPropertyDetailView,
    PublicPropertyListView,
)
from viewings.views import (
    ManagedViewingRequestDetailView,
    ManagedViewingRequestListView,
    PrivateGuestReceiptView,
    PublicViewingRequestCreateView,
)

app_name = 'api'

urlpatterns = [
    path('reports/', PublicListingReportCreateView.as_view(), name='listing-report-create'),
    path('auth/csrf/', CsrfTokenView.as_view(), name='csrf-token'),
    path('auth/register/', RegistrationView.as_view(), name='register'),
    path('auth/invitations/accept/', DelegatedInvitationAcceptView.as_view(), name='invitation-accept'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', AccountMeView.as_view(), name='me'),
    path('auth/preferences/', AccountPreferencesView.as_view(), name='preferences'),
    path('auth/preferences/reset/', AccountPreferencesResetView.as_view(), name='preferences-reset'),
    path('auth/activity/', AccountActivityView.as_view(), name='activity'),
    path('favorites/', FavoriteListCreateView.as_view(), name='favorite-list'),
    path('favorites/<int:property_id>/', FavoriteDeleteView.as_view(), name='favorite-delete'),
    path('amenities/', PublicAmenityListView.as_view(), name='amenity-list'),
    path('properties/', PublicPropertyListView.as_view(), name='property-list'),
    path('properties/<slug:slug>/', PublicPropertyDetailView.as_view(), name='property-detail'),
    path('viewing-requests/', PublicViewingRequestCreateView.as_view(), name='viewing-request-create'),
    path(
        'viewing-requests/receipt/',
        PrivateGuestReceiptView.as_view(),
        name='viewing-request-receipt',
    ),
    path('owner/properties/', ManagedPropertyListCreateView.as_view(), name='managed-property-list'),
    path('owner/properties/<int:pk>/', ManagedPropertyDetailView.as_view(), name='managed-property-detail'),
    path(
        'owner/properties/<int:pk>/submit/',
        ManagedPropertySubmitView.as_view(),
        name='managed-property-submit',
    ),
    path(
        'owner/properties/<int:property_id>/images/',
        ManagedPropertyImageListCreateView.as_view(),
        name='managed-property-images',
    ),
    path(
        'owner/properties/<int:property_id>/images/<int:pk>/',
        ManagedPropertyImageDetailView.as_view(),
        name='managed-property-image-detail',
    ),
    path('owner/viewing-requests/', ManagedViewingRequestListView.as_view(), name='managed-viewing-list'),
    path(
        'owner/viewing-requests/<int:pk>/',
        ManagedViewingRequestDetailView.as_view(),
        name='managed-viewing-detail',
    ),
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path(
        'admin/delegated-accounts/',
        AdminDelegatedAccountListCreateView.as_view(),
        name='admin-delegated-account-list',
    ),
    path(
        'admin/delegated-accounts/<int:pk>/',
        AdminDelegatedAccountDetailView.as_view(),
        name='admin-delegated-account-detail',
    ),
    path('admin/properties/', AdminPropertyListView.as_view(), name='admin-property-list'),
    path('admin/properties/<int:pk>/', AdminPropertyDetailView.as_view(), name='admin-property-detail'),
    path(
        'admin/properties/<int:property_id>/brokers/',
        AdminBrokerAssignmentListCreateView.as_view(),
        name='admin-broker-assignment-list',
    ),
    path(
        'admin/properties/<int:property_id>/brokers/<int:broker_id>/',
        AdminBrokerAssignmentDetailView.as_view(),
        name='admin-broker-assignment-detail',
    ),
    path('admin/reports/', AdminListingReportListView.as_view(), name='admin-report-list'),
    path('admin/reports/<int:pk>/', AdminListingReportDetailView.as_view(), name='admin-report-detail'),
    path('admin/audit-events/', AdminAuditEventListView.as_view(), name='admin-audit-event-list'),
]
