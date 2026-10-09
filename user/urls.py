from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='user_home'),
    path('listings/', views.listings, name='user_listings'),
    path('property/<slug:slug>/', views.property_detail, name='user_property_detail'),
    path('viewing-request/', views.viewing_request, name='user_viewing_request'),
    path('viewing-request/<int:property_id>/', views.viewing_request, name='user_property_request'),
    path('viewing-request/status/', views.viewing_request_status, name='user_viewing_request_status'),
]
