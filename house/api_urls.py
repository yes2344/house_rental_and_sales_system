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
    BrokerageSettingsView,
    ManagedHomepageNoteDetailView,
    ManagedHomepageNoteListCreateView,
    PublicListingReportCreateView,
    PublicHomepageNoteListView,
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
    ManagedPropertyPublicationView,
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
    path('homepage-notes/', PublicHomepageNoteListView.as_view(), name='homepage-note-list'),
    path('brokerage/contact/', BrokerageSettingsView.as_view(), name='brokerage-contact'),
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
    path('management/properties/', ManagedPropertyListCreateView.as_view(), name='managed-property-list'),
    path('management/homepage-notes/', ManagedHomepageNoteListCreateView.as_view(), name='managed-homepage-note-list'),
    path('management/homepage-notes/<int:pk>/', ManagedHomepageNoteDetailView.as_view(), name='managed-homepage-note-detail'),
    path('management/properties/<int:pk>/', ManagedPropertyDetailView.as_view(), name='managed-property-detail'),
    path(
        'management/properties/<int:pk>/publication/',
        ManagedPropertyPublicationView.as_view(),
        name='managed-property-publication',
    ),
    path(
        'management/properties/<int:property_id>/images/',
        ManagedPropertyImageListCreateView.as_view(),
        name='managed-property-images',
    ),
    path(
        'management/properties/<int:property_id>/images/<int:pk>/',
        ManagedPropertyImageDetailView.as_view(),
        name='managed-property-image-detail',
    ),
    path('management/viewing-requests/', ManagedViewingRequestListView.as_view(), name='managed-viewing-list'),
    path(
        'management/viewing-requests/<int:pk>/',
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
