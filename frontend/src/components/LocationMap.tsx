import { useEffect, useRef } from 'react';
import L from 'leaflet';
import {
  LayersControl,
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
  satelliteLabel: string;
  streetMapLabel: string;
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
      map.setView([coordinates.latitude, coordinates.longitude], Math.max(map.getZoom(), 16));
    }
  }, [coordinates, map]);

  return null;
}

export function LocationMap({
  coordinates,
  interactive = false,
  onCoordinatesChange,
  markerLabel,
  satelliteLabel,
  streetMapLabel,
  zoom = 16,
}: LocationMapProps) {
  const markerRef = useRef<L.Marker>(null);
  const center: L.LatLngExpression = coordinates
    ? [coordinates.latitude, coordinates.longitude]
    : DEBRE_MARKOS_MAP_VIEW;

  return (
    <MapContainer
      className="property-map"
      center={center}
      zoom={coordinates ? zoom : 13}
      scrollWheelZoom
      keyboard
    >
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name={satelliteLabel}>
          <TileLayer
            attribution='Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            maxNativeZoom={19}
            maxZoom={20}
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name={streetMapLabel}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
      </LayersControl>
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
