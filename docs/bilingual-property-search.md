# Bilingual property search

Public property search is performed by `BilingualPropertySearchFilter` on the
server. It composes with the existing public-property queryset, filters, result
ordering, and pagination; it does not load listings into the browser to search
them. Structured search concepts filter their model fields (for example,
bedroom and bathroom counts, listing type, property type, amenity, and rental
frequency). Remaining words search published property text and localized
amenity/location names.

## Terminology

The maintainable dictionary is `properties/search_terms.py`. Each
`SearchConcept` contains a canonical kind/value and explicit English and
Amharic aliases. Matching normalizes text to Unicode NFC, case-folds it, folds
repeated whitespace, and treats punctuation as token boundaries. Ge'ez
characters are retained; no transliteration or Unicode-wide character removal
is performed. English connectors such as “and” and “with” do not become text
search terms.

The only explicit Amharic concept alias currently enabled is the verified
mapping supplied for this feature: `መታጠቢያ` → bathroom count. A bare bathroom
term finds listings with at least one bathroom; a numeric query such as
`2 bathrooms` or `bathroom 2` filters the structured count. The dictionary
contains English aliases for the supported property types, amenities,
listing types, counts, rental periods, and search intent. Other Amharic
concept translations are intentionally not asserted until verified. Existing
Amharic amenity and location display names remain searchable as stored.

To add a synonym, add it to the appropriate `SearchConcept.aliases_en` or
`aliases_am` tuple in `SEARCH_CONCEPTS`. Keep each alias attached to one
canonical concept; duplicate aliases for different concepts fail module
initialization rather than silently changing meaning. Add an API test proving
the intended structured result set before treating a new alias as supported.

## Location names and aliases

`Location.name` and `Location.name_am` are searched along with active location
records. Authorized settings managers can maintain `aliases_en` and
`aliases_am` through `PATCH /api/v1/management/locations/{id}/`. Alias lists
are bounded to 20 entries, normalized on write, and do not create duplicate
location records. Search suggestions use `GET /api/v1/locations/?search=...`
and return at most 20 matches. Selecting a suggestion submits its stable
`location_id`; typed text remains supported when no suggestion is selected.
The existing administrative location cascade also uses stable IDs.

No Debre Markos or Addis Ababa location aliases are seeded by this feature.
Administrators must enter verified local names and aliases from an authoritative
source before users can rely on them.

## Limitations

Search does not use stemming, transliteration, fuzzy matching, or automatic
spelling correction. Amharic concept equivalence is deliberately limited to
the verified bathroom term until additional translations are reviewed. Unknown
Amharic text is preserved and searched against existing text/name fields; it
does not raise an error. Location suggestions are bounded, but the existing
administrative cascade continues to use its established full-location request.
