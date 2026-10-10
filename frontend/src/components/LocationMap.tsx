import { useEffect, useRef } from 'react';
import L from 'leaflet';
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import 'leaflet/dist/leaflet.css';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

export interface PropertyCoordinates {
  latitude: number;
  longitude: number;
}

interface LocationMapProps {
  coordinates: PropertyCoordinates | null;
  interactive?: boolean;
  onCoordinatesChange?: (coordinates: PropertyCoordinates) => void;
  markerLabel: string;
  zoom?: number;
}

const DEBRE_MARKOS_MAP_VIEW: L.LatLngTuple = [10.333, 37.733];

function formatCoordinates(coordinates: PropertyCoordinates): string {
  return `${coordinates.latitude.toFixed(6)}, ${coordinates.longitude.toFixed(6)}`;
}

function MapClickHandler({ onCoordinatesChange }: {
  onCoordinatesChange: (coordinates: PropertyCoordinates) => void;
}) {
  useMapEvents({
    click(event) {
      onCoordinatesChange({
        latitude: event.latlng.lat,
        longitude: event.latlng.lng,
      });
    },
  });
  return null;
}

function MapFocus({ coordinates }: { coordinates: PropertyCoordinates | null }) {
  const map = useMap();

  useEffect(() => {
    if (coordinates) {
      map.setView([coordinates.latitude, coordinates.longitude], Math.max(map.getZoom(), 15));
    }
  }, [coordinates, map]);

  return null;
}

export function LocationMap({
  coordinates,
  interactive = false,
  onCoordinatesChange,
  markerLabel,
  zoom = 15,
}: LocationMapProps) {
  const markerRef = useRef<L.Marker>(null);
  const center: L.LatLngExpression = coordinates
    ? [coordinates.latitude, coordinates.longitude]
    : DEBRE_MARKOS_MAP_VIEW;

  return (
    <MapContainer
      className="property-map"
      center={center}
      zoom={coordinates ? zoom : 12}
      scrollWheelZoom
      keyboard
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {interactive && onCoordinatesChange && (
        <MapClickHandler onCoordinatesChange={onCoordinatesChange} />
      )}
      <MapFocus coordinates={coordinates} />
      {coordinates && (
        <Marker
          position={[coordinates.latitude, coordinates.longitude]}
          draggable={interactive}
          title={markerLabel}
          alt={markerLabel}
          ref={markerRef}
          eventHandlers={interactive && onCoordinatesChange ? {
            dragend: () => {
              const marker = markerRef.current;
              if (!marker) return;
              const point = marker.getLatLng();
              onCoordinatesChange({ latitude: point.lat, longitude: point.lng });
            },
          } : undefined}
        >
          <Popup>{markerLabel}<br />{formatCoordinates(coordinates)}</Popup>
        </Marker>
      )}
    </MapContainer>
  );
}
