import django_filters
from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend

from properties.location_search import location_subtree_ids, matching_location_subtree_ids
from properties.models import Location, Property


class PublicPropertyOrderingFilter(BaseFilterBackend):
    ordering_param = 'ordering'
    default_ordering = '-created_at'
    allowed_orderings = {
        '-created_at',
        'created_at',
        '-price',
        'price',
    }

    def filter_queryset(self, request, queryset, view):
        if len(request.query_params.getlist(self.ordering_param)) > 1:
            raise ValidationError({
                self.ordering_param: 'Provide one property sort order only.',
            })
        ordering = request.query_params.get(self.ordering_param, self.default_ordering)
        if ordering not in self.allowed_orderings:
            raise ValidationError({
                self.ordering_param: 'Choose one of the supported property sort orders.',
            })

        if ordering in {'price', '-price'}:
            queryset = queryset.annotate(
                _price_sort_group=Case(
                    When(listing_type=Property.ListingType.SALE, then=Value(0)),
                    When(
                        listing_type=Property.ListingType.RENT,
                        rental_frequency=Property.RentalFrequency.DAILY,
                        then=Value(1),
                    ),
                    When(
                        listing_type=Property.ListingType.RENT,
                        rental_frequency=Property.RentalFrequency.WEEKLY,
                        then=Value(2),
                    ),
                    When(
                        listing_type=Property.ListingType.RENT,
                        rental_frequency=Property.RentalFrequency.MONTHLY,
                        then=Value(3),
                    ),
                    When(
                        listing_type=Property.ListingType.RENT,
                        rental_frequency=Property.RentalFrequency.YEARLY,
                        then=Value(4),
                    ),
                    default=Value(5),
                    output_field=IntegerField(),
                ),
            )
            return queryset.order_by('_price_sort_group', ordering, 'pk')

        return queryset.order_by(ordering, '-pk' if ordering == '-created_at' else 'pk')


class PublicPropertyFilter(django_filters.FilterSet):
    listing_type = django_filters.ChoiceFilter(choices=Property.ListingType.choices)
    property_type = django_filters.ChoiceFilter(choices=Property.PROPERTY_TYPES)
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
    city_id = django_filters.NumberFilter(method='filter_location')

    class Meta:
        model = Property
        fields = ['status', 'location']

    def filter_amenities(self, queryset, name, value):
        slugs = [slug.strip() for slug in value.split(',') if slug.strip()]
        for slug in slugs:
            queryset = queryset.filter(amenities__slug=slug)
        return queryset.distinct()

    def filter_location(self, queryset, name, value):
        location = Location.objects.filter(pk=value).first()
        if location is None:
            raise ValidationError({name: 'Choose an active location.'})
        if not location.is_active:
            return queryset.none()

        if name == 'city_id' and location.location_type not in {
            Location.Type.CITY,
            Location.Type.CITY_ADMINISTRATION,
        }:
            raise ValidationError({name: 'Choose an active city or city administration.'})

        if name == 'location_id':
            raw_city_id = self.data.get('city_id')
            if raw_city_id:
                try:
                    city_id = int(raw_city_id)
                except (TypeError, ValueError):
                    city_id = None
                if city_id:
                    city = Location.objects.filter(
                        pk=city_id,
                        is_active=True,
                        location_type__in=[Location.Type.CITY, Location.Type.CITY_ADMINISTRATION],
                    ).first()
                    if city is None:
                        raise ValidationError({
                            'city_id': 'Choose an active city or city administration.',
                        })
                    if location.pk not in location_subtree_ids({city.pk}):
                        raise ValidationError({
                            name: 'Choose a location within the selected city.',
                        })

        return queryset.filter(
            administrative_location_id__in=location_subtree_ids({location.pk})
        )

    def filter_location_text(self, queryset, name, value):
        matching_ids = matching_location_subtree_ids(value)
        location_match = Q(location__icontains=value)
        if matching_ids:
            location_match |= Q(administrative_location_id__in=matching_ids)
        return queryset.filter(location_match)
