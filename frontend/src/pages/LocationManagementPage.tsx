import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { MapPinned, Plus, Save, X } from 'lucide-react';

import { getApiFieldErrors, getErrorMessage } from '../api/client';
import {
  createManagedLocation,
  getManagedLocations,
  updateManagedLocation,
  type ManagedLocationPayload,
  type ManagedLocationType,
} from '../api/management';
import type { MarketplaceLocation } from '../api/properties';
import type { Locale, MessageKey } from '../i18n';

interface LocationManagementPageProps {
  locale: Locale;
  text: (key: MessageKey) => string;
}

interface LocationFormValues {
  name: string;
  name_am: string;
  aliases_en: string;
  aliases_am: string;
  location_type: ManagedLocationType;
  parent: string;
  is_active: boolean;
  display_order: string;
}

const emptyForm: LocationFormValues = {
  name: '',
  name_am: '',
  aliases_en: '',
  aliases_am: '',
  location_type: 'country',
  parent: '',
  is_active: true,
  display_order: '0',
};

const locationTypes: ManagedLocationType[] = [
  'country',
  'region',
  'city_administration',
  'city',
  'subcity',
  'woreda',
  'neighborhood',
];

function fromLocation(location: MarketplaceLocation): LocationFormValues {
  return {
    name: location.name,
    name_am: location.name_am,
    aliases_en: location.aliases_en.join(', '),
    aliases_am: location.aliases_am.join(', '),
    location_type: location.location_type,
    parent: location.parent_id === null ? '' : String(location.parent_id),
    is_active: location.is_active,
    display_order: String(location.display_order),
  };
}

function toPayload(values: LocationFormValues): ManagedLocationPayload {
  return {
    name: values.name.trim(),
    name_am: values.name_am.trim(),
    aliases_en: values.aliases_en.split(',').map((alias) => alias.trim()).filter(Boolean),
    aliases_am: values.aliases_am.split(',').map((alias) => alias.trim()).filter(Boolean),
    location_type: values.location_type,
    parent: values.parent ? Number(values.parent) : null,
    is_active: values.is_active,
    display_order: Number(values.display_order) || 0,
  };
}

export function LocationManagementPage({ locale, text }: LocationManagementPageProps) {
  const [locations, setLocations] = useState<MarketplaceLocation[]>([]);
  const [values, setValues] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState('');

  const loadLocations = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    try {
      setLocations(await getManagedLocations(signal));
      setError('');
    } catch (loadError) {
      if (!signal?.aborted) setError(getErrorMessage(loadError));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadLocations(controller.signal);
    return () => controller.abort();
  }, [loadLocations]);

  const locationById = useMemo(
    () => new Map(locations.map((location) => [location.id, location])),
    [locations],
  );
  const filteredLocations = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase();
    return locations.filter((location) => {
      if (!normalizedSearch) return true;
      const parentName = location.parent_id === null ? '' : locationById.get(location.parent_id)?.name ?? '';
      return [location.name, location.name_am, parentName, ...location.aliases_en, ...location.aliases_am]
        .some((value) => value.toLocaleLowerCase().includes(normalizedSearch));
    });
  }, [locationById, locations, search]);

  const startEditing = (location: MarketplaceLocation) => {
    setEditingId(location.id);
    setValues(fromLocation(location));
    setFieldErrors({});
    setError('');
    setSuccess('');
  };

  const resetForm = () => {
    setEditingId(null);
    setValues(emptyForm);
    setFieldErrors({});
    setError('');
    setSuccess('');
  };

  const updateValue = <K extends keyof LocationFormValues>(key: K, value: LocationFormValues[K]) => {
    setValues((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => ({ ...current, [key]: '' }));
    setError('');
    setSuccess('');
  };

  const saveLocation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    setFieldErrors({});
    try {
      const payload = toPayload(values);
      if (editingId === null) await createManagedLocation(payload);
      else await updateManagedLocation(editingId, payload);
      setLocations(await getManagedLocations());
      resetForm();
      setSuccess(text(editingId === null ? 'locationCreated' : 'locationUpdated'));
    } catch (saveError) {
      setError(getErrorMessage(saveError));
      setFieldErrors(getApiFieldErrors(saveError));
    } finally {
      setSaving(false);
    }
  };

  const localizedLocationType = (type: string) => text(
    ({
      country: 'locationCountry',
      region: 'locationRegion',
      city_administration: 'locationCityAdministration',
      city: 'locationCity',
      subcity: 'locationSubcity',
      woreda: 'locationWoreda',
      neighborhood: 'locationNeighborhood',
    } as Record<string, MessageKey>)[type] ?? 'administrativeLocation',
  );

  return (
    <main className="manager-page location-management-page" id="main-content">
      <header className="manager-page-header">
        <div>
          <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text('managerContactSettings')}</p>
          <h1>{text('locationManagementTitle')}</h1>
          <p>{text('locationManagementDescription')}</p>
        </div>
      </header>

      <div className="location-management-grid">
        <section className="manager-panel location-editor">
          <div className="manager-panel-heading">
            <h2>{editingId === null ? text('addLocation') : text('editLocation')}</h2>
            {editingId !== null && (
              <button className="button button-secondary" type="button" onClick={resetForm}>
                <X size={15} aria-hidden="true" />{text('cancelEdit')}
              </button>
            )}
          </div>
          <form className="manager-form-grid" onSubmit={saveLocation}>
            <label className="filter-label">{text('locationName')}
              <input className="filter-input" required maxLength={120} value={values.name} onChange={(event) => updateValue('name', event.target.value)} />
              {fieldErrors.name && <small role="alert">{fieldErrors.name}</small>}
            </label>
            <label className="filter-label">{text('locationNameAm')}
              <input className="filter-input" maxLength={120} value={values.name_am} onChange={(event) => updateValue('name_am', event.target.value)} />
              {fieldErrors.name_am && <small role="alert">{fieldErrors.name_am}</small>}
            </label>
            <label className="filter-label">{text('locationType')}
              <select className="filter-select" value={values.location_type} onChange={(event) => {
                const selectedType = locationTypes.find((type) => type === event.target.value);
                if (selectedType) updateValue('location_type', selectedType);
              }}>
                {locationTypes.map((type) => <option key={type} value={type}>{localizedLocationType(type)}</option>)}
              </select>
            </label>
            <label className="filter-label">{text('locationParent')}
              <select className="filter-select" value={values.parent} onChange={(event) => updateValue('parent', event.target.value)}>
                <option value="">{text('noParent')}</option>
                {locations.filter((location) => location.id !== editingId).map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name} · {localizedLocationType(location.location_type)}
                    {!location.is_active ? ` (${text('statusInactive')})` : ''}
                  </option>
                ))}
              </select>
              {fieldErrors.parent && <small role="alert">{fieldErrors.parent}</small>}
            </label>
            <label className="filter-label">{text('locationAliasesEn')}
              <input className="filter-input" value={values.aliases_en} onChange={(event) => updateValue('aliases_en', event.target.value)} placeholder={text('locationAliasesEnPlaceholder')} />
            </label>
            <label className="filter-label">{text('locationAliasesAm')}
              <input className="filter-input" value={values.aliases_am} onChange={(event) => updateValue('aliases_am', event.target.value)} placeholder={text('locationAliasesAmPlaceholder')} />
            </label>
            <label className="filter-label">{text('displayOrder')}
              <input className="filter-input" type="number" min="0" step="1" value={values.display_order} onChange={(event) => updateValue('display_order', event.target.value)} />
            </label>
            {editingId !== null && (
              <label className="location-active-toggle">
                <input type="checkbox" checked={values.is_active} onChange={(event) => updateValue('is_active', event.target.checked)} />
                {text('locationActive')}
              </label>
            )}
            {error && <p className="manager-error location-form-message" role="alert">{error}</p>}
            {success && <p className="manager-success location-form-message" role="status">{success}</p>}
            <div className="location-form-actions">
              <button className="button button-primary" type="submit" disabled={saving}>
                {editingId === null ? <Plus size={15} aria-hidden="true" /> : <Save size={15} aria-hidden="true" />}
                {saving ? text('savingLocation') : text('saveLocation')}
              </button>
            </div>
          </form>
        </section>

        <section className="manager-panel location-list-panel">
          <div className="manager-panel-heading">
            <h2><MapPinned size={17} aria-hidden="true" />{text('configuredLocations')}</h2>
            <span>{locations.length}</span>
          </div>
          <label className="filter-label location-list-search">{text('searchLocations')}
            <input className="filter-input" value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          {error && locations.length === 0 && <p className="manager-error" role="alert">{error}</p>}
          {loading ? <p role="status">{text('loadingLocations')}</p> : filteredLocations.length === 0 ? (
            <p className="location-list-empty">{text('locationOptionsEmpty')}</p>
          ) : (
            <div className="location-table-wrap">
              <table className="manager-table location-table">
                <thead><tr>
                  <th>{text('locationName')}</th>
                  <th>{text('locationType')}</th>
                  <th>{text('locationParent')}</th>
                  <th>{text('listingStatus')}</th>
                  <th><span className="sr-only">{text('actions')}</span></th>
                </tr></thead>
                <tbody>
                  {filteredLocations.map((location) => (
                    <tr key={location.id}>
                      <td>
                        <strong>{locale === 'am' && location.name_am ? location.name_am : location.name}</strong>
                        {location.name_am && locale !== 'am' && <small>{location.name_am}</small>}
                      </td>
                      <td>{localizedLocationType(location.location_type)}</td>
                      <td>{location.parent_id === null ? '—' : locationById.get(location.parent_id)?.name ?? '—'}</td>
                      <td><span className={`status-pill ${location.is_active ? 'is-active' : 'is-inactive'}`}>
                        {text(location.is_active ? 'available' : 'statusInactive')}
                      </span></td>
                      <td><button className="button button-secondary location-edit-button" type="button" onClick={() => startEditing(location)}>
                        {text('editLocation')}
                      </button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
      <p className="location-management-note">{text('locationManagementNote')}</p>
    </main>
  );
}
