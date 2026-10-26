from properties.models import Location
from properties.search_terms import normalize_search_text


def matching_location_ids(value: str) -> set[int]:
    normalized = normalize_search_text(value)
    if not normalized:
        return set()
    matches = set()
    for location in Location.objects.filter(is_active=True).only(
        'id',
        'name',
        'name_am',
        'aliases_en',
        'aliases_am',
    ):
        searchable_values = [
            location.name,
            location.name_am,
            *(location.aliases_en or []),
            *(location.aliases_am or []),
        ]
        if any(
            normalized in normalize_search_text(searchable_value)
            for searchable_value in searchable_values
            if isinstance(searchable_value, str)
        ):
            matches.add(location.pk)
    return matches


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
