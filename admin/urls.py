from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='admin_dashboard'),
    path('logout/', views.portal_logout, name='admin_portal_logout'),
    path('properties/', views.property_list, name='admin_property_list'),
    path('properties/new/', views.property_form, name='admin_property_form'),
    path('properties/<int:pk>/edit/', views.property_form, name='admin_property_edit'),
    path('properties/<int:pk>/toggle/', views.toggle_property, name='admin_property_toggle'),
    path('properties/<int:pk>/delete/', views.delete_property, name='admin_property_delete'),
    path('delegated-accounts/', views.delegated_accounts, name='admin_delegated_accounts'),
]
