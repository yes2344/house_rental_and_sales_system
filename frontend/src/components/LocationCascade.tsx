import { useEffect, useState } from 'react';

import { getManagedLocations } from '../api/management';
import { getLocations, type MarketplaceLocation } from '../api/properties';
import type { Locale, MessageKey } from '../i18n';

interface LocationCascadeProps {
  value: string;
  locale: Locale;
  onChange: (locationId: string) => void;
  text: (key: MessageKey) => string;
  required?: boolean;
  management?: boolean;
}

const locationTypeMessages: Record<string, MessageKey> = {
  country: 'locationCountry',
  region: 'locationRegion',
  city_administration: 'locationCityAdministration',
  city: 'locationCity',
  subcity: 'locationSubcity',
  woreda: 'locationWoreda',
  neighborhood: 'locationNeighborhood',
};

export function LocationCascade({
  value,
  locale,
  onChange,
  text,
  required = false,
  management = false,
}: LocationCascadeProps) {
  const [locations, setLocations] = useState<MarketplaceLocation[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    void (management
      ? getManagedLocations(controller.signal)
      : getLocations(undefined, controller.signal, true))
      .then(setLocations)
      .catch(() => {
        if (!controller.signal.aborted) setError('Administrative locations could not be loaded.');
      });
    return () => controller.abort();
  }, [management]);

  useEffect(() => {
    const selectedId = Number(value);
    if (!Number.isInteger(selectedId) || selectedId < 1 || locations.length === 0) {
      if (!value) setSelectedIds([]);
      return;
    }
    const byId = new Map(locations.map((location) => [location.id, location]));
    const path: number[] = [];
    let current: MarketplaceLocation | undefined = byId.get(selectedId);
    while (current) {
      path.unshift(current.id);
      current = current.parent_id === null ? undefined : byId.get(current.parent_id);
    }
    setSelectedIds(path);
  }, [locations, value]);

  const choose = (level: number, rawValue: string) => {
    const nextIds = selectedIds.slice(0, level);
    if (rawValue) nextIds.push(Number(rawValue));
    setSelectedIds(nextIds);
    onChange(nextIds.length ? String(nextIds[nextIds.length - 1]) : '');
  };

  const levels: MarketplaceLocation[][] = [];
  let parentId: number | null = null;
  for (let level = 0; level < 8; level += 1) {
    const selectedAtLevel = selectedIds[level];
    const options = locations.filter(
      (location) => location.parent_id === parentId
        && (location.is_active || location.id === selectedAtLevel),
    );
    if (options.length === 0) break;
    levels.push(options);
    parentId = selectedIds[level] ?? null;
    if (parentId === null) break;
  }

  const selectedLocationTypes = selectedIds
    .map((id) => locations.find((location) => location.id === id)?.location_type);
  const hasCity = selectedLocationTypes.some(
    (type) => type === 'city' || type === 'city_administration',
  );
  const hasSubcity = selectedLocationTypes.includes('subcity');

  return (
    <fieldset className="location-cascade">
      <legend>{text('administrativeLocation')}</legend>
      <div className="filter-two-columns">
        {levels.map((options, level) => (
          <label className="filter-label" key={level}>
            {text(locationTypeMessages[options[0]?.location_type] ?? 'administrativeLocation')}
            <select
              className="filter-select"
              value={selectedIds[level] ?? ''}
              disabled={options.every((location) => !location.is_active)}
              required={required && (
                level === 0
                || (options.some((location) => location.location_type === 'city'
                  || location.location_type === 'city_administration') && !hasCity)
                || (options.some((location) => location.location_type === 'subcity') && hasCity && !hasSubcity)
              )}
              onChange={(event) => choose(level, event.target.value)}
            >
              <option value="">{text('selectOption')}</option>
              {options.map((location) => (
                <option
                  key={location.id}
                  value={location.id}
                  disabled={!location.is_active && selectedIds[level] !== location.id}
                >
                  {locale === 'am' && location.name_am ? location.name_am : location.name}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      {error && <small role="alert">{text('locationLoadError')}</small>}
      {!error && locations.length === 0 && <small>{text('locationOptionsEmpty')}</small>}
    </fieldset>
  );
}
