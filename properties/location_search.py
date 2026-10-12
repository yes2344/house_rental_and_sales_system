from django.db.models import Q, TextField
from django.db.models.functions import Cast

from properties.models import Location
from properties.search_terms import normalize_search_text


def matching_location_ids(value: str) -> set[int]:
    normalized = normalize_search_text(value)
    if not normalized:
        return set()
    return set(
        Location.objects.filter(is_active=True)
        .annotate(
            aliases_en_text=Cast('aliases_en', TextField()),
            aliases_am_text=Cast('aliases_am', TextField()),
        )
        .filter(
            Q(name__icontains=value.strip())
            | Q(name_am__icontains=value.strip())
            | Q(aliases_en_text__icontains=normalized)
            | Q(aliases_am_text__icontains=normalized)
        )
        .values_list('pk', flat=True)
    )


def location_subtree_ids(root_ids: set[int]) -> set[int]:
    matching_ids = set(
        Location.objects.filter(pk__in=root_ids, is_active=True).values_list('pk', flat=True)
    )
    frontier = set(matching_ids)
    while frontier:
        child_ids = set(
            Location.objects.filter(
                parent_id__in=frontier,
                is_active=True,
            ).values_list('pk', flat=True)
        ) - matching_ids
        matching_ids.update(child_ids)
        frontier = child_ids
    return matching_ids


def matching_location_subtree_ids(value: str) -> set[int]:
    return location_subtree_ids(matching_location_ids(value))
