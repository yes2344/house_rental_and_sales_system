# Property maps

> This document describes the previous product behavior. Node public property
> browsing is available, but property-management/map editing routes are still
> pending. See [`../backend/docs/API_MIGRATION_STATUS.md`](../backend/docs/API_MIGRATION_STATUS.md).

Property locations use optional latitude and longitude values. Exact
coordinates are private by default; a listing manager must explicitly enable
public display. The existing `location` value remains the public-facing area,
so use a neighborhood when the precise address should stay private.

The React property forms use Leaflet and default to Esri World Imagery
satellite tiles, with a selectable OpenStreetMap street layer. These public
tile services do not provide a guaranteed production SLA; review provider
terms before significant traffic. Do not bulk-download or prefetch tiles.

Address search is not included. The public Nominatim geocoder has strict usage limits and is not a free unlimited production search API. The map picker supports direct selection, dragging, manual coordinates, and browser geolocation instead.

The frontend requires no map-specific environment variables. Browser
geolocation requires a secure context (HTTPS in deployment; localhost is
allowed during development). No Node management API or schema bootstrap for
this feature is currently included.
