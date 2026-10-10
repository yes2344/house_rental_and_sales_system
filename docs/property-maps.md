# Property maps

Property locations use optional latitude and longitude values. Exact coordinates are private by default; a listing manager must explicitly enable public display. The existing `location` value remains the public-facing address or area, so use a neighborhood or other approximate area there when the precise address should stay private.

The public React property-registration form and the legacy Django admin property form both use Leaflet with OpenStreetMap's standard tile service to select a location. The legacy form also supports manual coordinates and browser geolocation. No API key or paid account is required for local development. The map credits OpenStreetMap on screen. The public tile servers have a usage policy and are not an unlimited or guaranteed production hosting service; review that policy and arrange an appropriate tile provider before significant production traffic. Do not bulk-download or prefetch tiles.

Address search is not included. The public Nominatim geocoder has strict usage limits and is not a free unlimited production search API. The map picker supports direct selection, dragging, manual coordinates, and browser geolocation instead.

Run the additive schema migration before starting the application:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

The frontend requires no map-specific environment variables. Browser geolocation requires a secure context (HTTPS in deployment; localhost is allowed during development).
