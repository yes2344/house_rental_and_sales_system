import django_filters
from django.db.models import Q

from properties.location_search import location_subtree_ids, matching_location_subtree_ids
from properties.models import Property


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
    location = django_filters.CharFilter(method='filter_location_text')
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
        return queryset.filter(
            administrative_location_id__in=location_subtree_ids({int(value)})
        )

    def filter_location_text(self, queryset, name, value):
        matching_ids = matching_location_subtree_ids(value)
        location_match = Q(location__icontains=value)
        if matching_ids:
            location_match |= Q(administrative_location_id__in=matching_ids)
        return queryset.filter(location_match)
