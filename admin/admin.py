from django.contrib import admin

from accounts.models import Profile
from admin.models import AdminAuditEvent
from properties.models import ListingReport, Property, PropertyAgentAssignment


class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Property)
class PropertyAdmin(ReadOnlyAdmin):
    exclude = ('latitude', 'longitude', 'exact_location_is_public')
    list_display = ('id', 'title', 'listing_type', 'status', 'publication_status', 'created_at')
    list_filter = ('listing_type', 'status', 'publication_status', 'property_type')
    search_fields = ('title', 'location', 'owner__username')

    def get_readonly_fields(self, request, obj=None):
        excluded = set(self.get_exclude(request, obj) or ())
        return [field.name for field in self.model._meta.fields if field.name not in excluded]


@admin.register(PropertyAgentAssignment)
class PropertyAgentAssignmentAdmin(ReadOnlyAdmin):
    list_display = ('property', 'agent', 'granted_by', 'granted_at')
    search_fields = ('property__title', 'agent__username')


@admin.register(ListingReport)
class ListingReportAdmin(ReadOnlyAdmin):
    list_display = ('id', 'property_title', 'reason', 'status', 'created_at', 'reviewed_by')
    list_filter = ('status', 'reason')
    search_fields = ('property_title', 'reporter_name', 'reporter_email')


@admin.register(Profile)
class ProfileAdmin(ReadOnlyAdmin):
    list_display = ('user', 'role', 'agent_approved', 'created_at')
    list_filter = ('role', 'agent_approved')
    search_fields = ('user__username', 'user__email')


@admin.register(AdminAuditEvent)
class AdminAuditEventAdmin(ReadOnlyAdmin):
    list_display = ('id', 'actor_username', 'action', 'object_type', 'object_id', 'created_at')
    list_filter = ('action', 'object_type')
    search_fields = ('actor_username', 'object_id')
