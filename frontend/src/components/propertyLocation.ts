export function hasPublicCoordinates(
  latitude: number | string | null,
  longitude: number | string | null,
): boolean {
  if (latitude === null || longitude === null) return false;
  const lat = Number(latitude);
  const lng = Number(longitude);
  return Number.isFinite(lat) && lat >= -90 && lat <= 90
    && Number.isFinite(lng) && lng >= -180 && lng <= 180;
}

export function openStreetMapUrl(latitude: number, longitude: number): string {
  return `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=17/${latitude}/${longitude}`;
}

export function openStreetMapDirectionsUrl(latitude: number, longitude: number): string {
  return `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=%3B${latitude}%2C${longitude}`;
}
