import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchConcept:
    kind: str
    value: str = ''
    aliases_en: tuple[str, ...] = ()
    aliases_am: tuple[str, ...] = ()


# Add verified synonyms here. Matching is phrase-based; Ge'ez characters are
# normalized to NFC and preserved, while English is case-folded.
SEARCH_CONCEPTS = (
    SearchConcept('property_type', 'house', ('house', 'houses', 'home', 'homes')),
    SearchConcept('property_type', 'apartment', ('apartment', 'apartments', 'flat', 'flats')),
    SearchConcept('property_type', 'condominium', ('condominium', 'condominiums', 'condo', 'condos')),
    SearchConcept('property_type', 'villa', ('villa', 'villas')),
    SearchConcept('property_type', 'land', ('land', 'plot', 'plots')),
    SearchConcept('property_type', 'office', ('office', 'offices')),
    SearchConcept('property_type', 'shop', ('shop', 'shops', 'store', 'stores')),
    SearchConcept('property_type', 'warehouse', ('warehouse', 'warehouses')),
    SearchConcept('listing_type', 'rent', ('rent', 'rental', 'rentals', 'lease', 'leasing')),
    SearchConcept('listing_type', 'sale', ('sale', 'sales', 'buy', 'purchase')),
    SearchConcept('count', 'bedrooms', ('bedroom', 'bedrooms', 'bed', 'beds')),
    SearchConcept('count', 'bathrooms', ('bathroom', 'bathrooms', 'bath', 'baths'), ('መታጠቢያ',)),
    SearchConcept('amenity', 'kitchen', ('kitchen', 'kitchens')),
    SearchConcept('amenity', 'living-room', ('living room', 'living rooms', 'lounge')),
    SearchConcept('amenity', 'parking', ('parking', 'car park', 'car parking')),
    SearchConcept('amenity', 'garden', ('garden', 'gardens')),
    SearchConcept('amenity', 'balcony', ('balcony', 'balconies')),
    SearchConcept('amenity', 'furnished', ('furnished', 'furnishing')),
    SearchConcept('amenity', 'unfurnished', ('unfurnished', 'not furnished')),
    SearchConcept('floor_area', 'area', ('area', 'size', 'floor area', 'floor size')),
    SearchConcept('amenity', 'water', ('water', 'water supply')),
    SearchConcept('amenity', 'electricity', ('electricity', 'power')),
    SearchConcept('amenity', 'security', ('security', 'secure')),
    SearchConcept('amenity', 'elevator', ('elevator', 'lift')),
    SearchConcept('amenity', 'internet', ('internet', 'wifi', 'wi fi')),
    SearchConcept('rental_frequency', 'daily', ('daily', 'per day')),
    SearchConcept('rental_frequency', 'weekly', ('weekly', 'per week')),
    SearchConcept('rental_frequency', 'monthly', ('monthly', 'per month')),
    SearchConcept('rental_frequency', 'yearly', ('yearly', 'annually', 'per year')),
    SearchConcept('intent', 'price', ('price', 'cost', 'costs')),
    SearchConcept('intent', 'location', ('location', 'place')),
    SearchConcept('availability', 'available', ('available', 'availability')),
)

SEARCH_CONNECTORS = {'and', 'with', 'in', 'for', 'of'}


def normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize('NFC', value).casefold()
    words = re.findall(r'[^\W_]+', normalized, flags=re.UNICODE)
    return ' '.join(words)


def tokenize_search_text(value: str) -> list[str]:
    normalized = normalize_search_text(value)
    return normalized.split() if normalized else []


def _alias_index() -> dict[tuple[str, ...], SearchConcept]:
    index: dict[tuple[str, ...], SearchConcept] = {}
    for concept in SEARCH_CONCEPTS:
        for alias in (*concept.aliases_en, *concept.aliases_am):
            tokens = tuple(tokenize_search_text(alias))
            if tokens:
                existing = index.get(tokens)
                if existing is not None and existing != concept:
                    raise ValueError(f'Search alias {alias!r} maps to multiple concepts.')
                index[tokens] = concept
    return index


def _parse_count(value: str) -> int | None:
    if not value.isdecimal() or len(value) > 3:
        return None
    return int(value)


CONCEPT_ALIASES = _alias_index()
MAX_ALIAS_TOKENS = max(map(len, CONCEPT_ALIASES), default=1)


def match_search_concepts(value: str) -> tuple[list[tuple[SearchConcept, int | None]], list[str]]:
    tokens = tokenize_search_text(value)
    concepts: list[tuple[SearchConcept, int | None]] = []
    remaining: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] in SEARCH_CONNECTORS:
            index += 1
            continue
        match: tuple[SearchConcept, int] | None = None
        for length in range(min(MAX_ALIAS_TOKENS, len(tokens) - index), 0, -1):
            candidate = CONCEPT_ALIASES.get(tuple(tokens[index:index + length]))
            if candidate is not None:
                match = (candidate, length)
                break
        if match is None:
            remaining.append(tokens[index])
            index += 1
            continue

        concept, length = match
        count: int | None = None
        if concept.kind == 'count':
            if concepts and concepts[-1][0].kind == 'count' and concepts[-1][1] is None and concepts[-1][0] is concept:
                concepts.pop()
                count = None
            before = tokens[index - 1] if index > 0 else ''
            after_index = index + length
            after = tokens[after_index] if after_index < len(tokens) else ''
            parsed_before = _parse_count(before)
            parsed_after = _parse_count(after)
            if parsed_before is not None:
                count = parsed_before
                if remaining and remaining[-1] == before:
                    remaining.pop()
            elif parsed_after is not None:
                count = parsed_after
                index += 1
        concepts.append((concept, count))
        index += length
    return concepts, remaining
