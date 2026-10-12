# Location management

Property locations use the existing `Location` table and parent/child hierarchy.
Properties keep a foreign key to one location record; translated names and
aliases do not create duplicate city or property records.

## Managing verified locations

An authorized broker or platform administrator with the existing
`settings.manage` permission can use **Management → Manage locations**. The
screen supports creating and editing location names, English and Amharic
display names, aliases, parent relationships, ordering, and active status.
The API records create/update actions in the administrative audit log. Physical
deletion is disabled; deactivation preserves historical property references.

The hierarchy accepts the levels country, region, city administration, city or
town, sub-city/kifle ketema, woreda, and neighborhood. Parent/child combinations
are validated by the `Location` model. Enter names and aliases only after
verifying them with an authoritative source. Do not create a second location
record to represent a translated spelling; use `name_am` or an alias instead.
Aliases are comma-separated in the management form and are normalized when
saved.

The development database had no configured location rows when this feature
work began. This change does not seed or invent Debre Markos or Addis Ababa
locations. The public city bar and location suggestions therefore show only
cities that an authorized manager has configured. The property form requires
an active city/town selection, and if that city has active direct sub-city
children, it also requires selection beneath one of those sub-cities.

## Search, filtering, and display

- Public location suggestions resolve to stable location IDs.
- `city_id` filters all listings in the selected city/town subtree; existing
  `location_id` filtering continues to support more specific hierarchy nodes.
- The public city bar and its area selector are populated from the active
  location API, not a frontend-maintained city list.
- Property cards, detail pages, and broker listing rows display the configured
  location path using the selected interface language, followed by any distinct
  free-text address information.
- Pagination, sorting, publication visibility, and existing property data are
  unchanged.

No database migration, seed operation, or destructive database action is
required for this feature.
