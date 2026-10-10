import django_filters

from properties.models import Property
from properties.models import Location


class PublicPropertyFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(
        choices=[
            (Property.Status.AVAILABLE, 'Available'),
            (Property.Status.LEGACY_ACTIVE, 'Available'),
        ],
    )
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_bedrooms = django_filters.NumberFilter(field_name='bedrooms', lookup_expr='gte')
    max_bedrooms = django_filters.NumberFilter(field_name='bedrooms', lookup_expr='lte')
    min_bathrooms = django_filters.NumberFilter(field_name='bathrooms', lookup_expr='gte')
    max_bathrooms = django_filters.NumberFilter(field_name='bathrooms', lookup_expr='lte')
    min_size = django_filters.NumberFilter(field_name='area_sqft', lookup_expr='gte')
    max_size = django_filters.NumberFilter(field_name='area_sqft', lookup_expr='lte')
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    amenities = django_filters.CharFilter(method='filter_amenities')
    location_id = django_filters.NumberFilter(method='filter_location')

    class Meta:
        model = Property
        fields = ['listing_type', 'property_type', 'status', 'location']

    def filter_amenities(self, queryset, name, value):
        slugs = [slug.strip() for slug in value.split(',') if slug.strip()]
        for slug in slugs:
            queryset = queryset.filter(amenities__slug=slug)
        return queryset.distinct()

    def filter_location(self, queryset, name, value):
        root_id = int(value)
        if not Location.objects.filter(pk=root_id, is_active=True).exists():
            return queryset.none()

        matching_ids = {root_id}
        frontier = {root_id}
        while frontier:
            child_ids = set(
                Location.objects.filter(
                    parent_id__in=frontier,
                    is_active=True,
                ).values_list('id', flat=True)
            )
            frontier = child_ids - matching_ids
            matching_ids.update(frontier)
        return queryset.filter(administrative_location_id__in=matching_ids)
