import { useEffect, useState } from 'react';

import { getLocations, type MarketplaceLocation } from '../api/properties';
import type { Locale } from '../i18n';

interface LocationCascadeProps {
  value: string;
  locale: Locale;
  onChange: (locationId: string) => void;
}

export function LocationCascade({ value, locale, onChange }: LocationCascadeProps) {
  const [locations, setLocations] = useState<MarketplaceLocation[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    void getLocations(undefined, controller.signal, true)
      .then(setLocations)
      .catch(() => {
        if (!controller.signal.aborted) setError('Administrative locations could not be loaded.');
      });
    return () => controller.abort();
  }, []);

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
    const options = locations.filter((location) => location.parent_id === parentId);
    if (options.length === 0) break;
    levels.push(options);
    parentId = selectedIds[level] ?? null;
    if (parentId === null) break;
  }

  return (
    <fieldset className="location-cascade">
      <legend>Administrative location (optional)</legend>
      <div className="filter-two-columns">
        {levels.map((options, level) => (
          <label className="filter-label" key={level}>
            {level === 0 ? 'Country / root location' : 'Child location'}
            <select
              className="filter-select"
              value={selectedIds[level] ?? ''}
              onChange={(event) => choose(level, event.target.value)}
            >
              <option value="">Any</option>
              {options.map((location) => (
                <option key={location.id} value={location.id}>
                  {locale === 'am' && location.name_am ? location.name_am : location.name}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      {error && <small role="alert">{error}</small>}
    </fieldset>
  );
}
