from django.contrib import admin
from properties.models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    exclude = ('latitude', 'longitude')
    list_display = ('name', 'location_type', 'parent', 'is_active', 'display_order')
    list_filter = ('location_type', 'is_active')
    search_fields = ('name', 'name_am', 'slug')
    ordering = ('location_type', 'display_order', 'name')
