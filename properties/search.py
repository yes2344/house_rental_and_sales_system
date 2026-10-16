from django.db.models import Q
from rest_framework.filters import BaseFilterBackend
from rest_framework.exceptions import ValidationError

from properties.location_search import matching_location_ids, matching_location_subtree_ids
from properties.models import Amenity, Property
from properties.search_terms import SearchConcept, match_search_concepts


def apply_search_concept(queryset, concept: SearchConcept, count: int | None):
    if concept.kind == 'property_type':
        return queryset.filter(property_type=concept.value)
    if concept.kind == 'listing_type':
        return queryset.filter(listing_type=concept.value)
    if concept.kind == 'count':
        lookup = 'bedrooms' if concept.value == 'bedrooms' else 'bathrooms'
        if count is None:
            return queryset.filter(**{f'{lookup}__gte': 1})
        return queryset.filter(**{lookup: count})
    if concept.kind == 'amenity':
        english_names = Q()
        for alias in concept.aliases_en:
            english_names |= Q(name__iexact=alias)
        amenity_ids = Amenity.objects.filter(
            Q(slug__iexact=concept.value)
            | Q(name__iexact=concept.value.replace('-', ' '))
            | english_names
            | Q(name_am__in=concept.aliases_am)
        ).values('pk')
        feature_name = concept.value.replace('-', ' ')
        return queryset.filter(
            Q(amenities__in=amenity_ids)
            | Q(features__icontains=feature_name)
        )
    if concept.kind == 'floor_area':
        return queryset.filter(Q(area_value__isnull=False) | Q(area_sqft__gt=0))
    if concept.kind == 'rental_frequency':
        return queryset.filter(
            listing_type=Property.ListingType.RENT,
            rental_frequency=concept.value,
        )
    if concept.kind == 'availability':
        return queryset.filter(status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE])
    return queryset


class BilingualPropertySearchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if len(request.query_params.getlist('search')) > 1:
            raise ValidationError({'search': 'Provide the search query only once.'})

        query = request.query_params.get('search', '')
        if not query.strip():
            return queryset

        concepts, remaining = match_search_concepts(query)
        for concept, count in concepts:
            queryset = apply_search_concept(queryset, concept, count)

        remaining_text = ' '.join(remaining)
        location_ids = matching_location_subtree_ids(remaining_text) if remaining_text else set()
        if location_ids:
            queryset = queryset.filter(administrative_location_id__in=location_ids)
        else:
            search_conditions = [
                Q(title__icontains=term)
                | Q(location__icontains=term)
                | Q(description__icontains=term)
                | Q(features__icontains=term)
                | Q(amenities__name__icontains=term)
                | Q(amenities__name_am__icontains=term)
                | Q(administrative_location__name__icontains=term)
                | Q(administrative_location__name_am__icontains=term)
                | Q(administrative_location_id__in=matching_location_ids(term))
                for term in remaining
            ]
            for condition in search_conditions:
                queryset = queryset.filter(condition)

        return queryset.distinct()
