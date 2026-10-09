import django_filters

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
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    amenities = django_filters.CharFilter(method='filter_amenities')

    class Meta:
        model = Property
        fields = ['listing_type', 'property_type', 'status', 'location']

    def filter_amenities(self, queryset, name, value):
        slugs = [slug.strip() for slug in value.split(',') if slug.strip()]
        for slug in slugs:
            queryset = queryset.filter(amenities__slug=slug)
        return queryset.distinct()
