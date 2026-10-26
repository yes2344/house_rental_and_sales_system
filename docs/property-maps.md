# Property maps

Property locations use optional latitude and longitude values. Exact coordinates are private by default; a listing manager must explicitly enable public display. The existing `location` value remains the public-facing address or area, so use a neighborhood or other approximate area there when the precise address should stay private.

The React and legacy Django property forms use Leaflet and default to Esri World Imagery satellite tiles, with a selectable OpenStreetMap street layer. Map controls allow users to zoom, pan, and select or drag the location marker. These public tile services do not provide a guaranteed production SLA, and satellite resolution varies by location; review each provider's terms and arrange an appropriate production tile service before significant traffic. Do not bulk-download or prefetch tiles. Both providers are attributed in the map control.

Address search is not included. The public Nominatim geocoder has strict usage limits and is not a free unlimited production search API. The map picker supports direct selection, dragging, manual coordinates, and browser geolocation instead.

Run the additive schema migration before starting the application:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

The frontend requires no map-specific environment variables. Browser geolocation requires a secure context (HTTPS in deployment; localhost is allowed during development).
