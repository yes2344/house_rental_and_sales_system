import { useEffect, useState, type FormEvent } from 'react';
import { getApiFieldErrors, getErrorMessage } from '../api/client';
import {
  createManagedBrokerAccount,
  deleteManagedBrokerAccount,
  getManagedBrokerAccounts,
  updateManagedBrokerAccount,
  type ManagedBrokerAccount,
} from '../api/management';
import { getLocationsByTypes, type MarketplaceLocation } from '../api/properties';
import type { MessageKey } from '../i18n';

interface BrokerAccountManagementPageProps {
  text: (key: MessageKey) => string;
}

interface BrokerEditValues {
  username: string;
  initial_password: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  is_active: boolean;
  assigned_city_id: string;
}

const emptyEditValues: BrokerEditValues = {
  username: '',
  initial_password: '',
  email: '',
  first_name: '',
  last_name: '',
  phone: '',
  is_active: true,
  assigned_city_id: '',
};

export function BrokerAccountManagementPage({ text }: BrokerAccountManagementPageProps) {
  const [accounts, setAccounts] = useState<ManagedBrokerAccount[]>([]);
  const [cities, setCities] = useState<MarketplaceLocation[]>([]);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [assignedCityId, setAssignedCityId] = useState('');
  const [editing, setEditing] = useState<ManagedBrokerAccount | null>(null);
  const [editValues, setEditValues] = useState<BrokerEditValues>(emptyEditValues);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getManagedBrokerAccounts(controller.signal),
      getLocationsByTypes(['city'], controller.signal),
    ])
      .then(([brokerAccounts, configuredCities]) => {
        setAccounts(brokerAccounts);
        setCities(configuredCities);
      })
      .catch((loadError: unknown) => {
        if (!controller.signal.aborted) setError(getErrorMessage(loadError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const createAccount = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!assignedCityId) {
      setFieldErrors({ assigned_city_id: text('selectOption') });
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    setFieldErrors({});
    try {
      const created = await createManagedBrokerAccount({
        username: username.trim(),
        password,
        assigned_city_id: Number(assignedCityId),
      });
      setAccounts((current) => [...current, created].sort((a, b) => a.username.localeCompare(b.username)));
      setUsername('');
      setPassword('');
      setAssignedCityId('');
      setSuccess(text('brokerCreated'));
    } catch (createError: unknown) {
      setError(getErrorMessage(createError));
      setFieldErrors(getApiFieldErrors(createError));
    } finally {
      setSaving(false);
    }
  };

  const beginEdit = (account: ManagedBrokerAccount) => {
    setEditing(account);
    setEditValues({
      username: account.username,
      initial_password: '',
      email: account.email,
      first_name: account.first_name,
      last_name: account.last_name,
      phone: account.phone,
      is_active: account.is_active,
      assigned_city_id: account.assigned_city_id === null ? '' : String(account.assigned_city_id),
    });
    setError('');
    setSuccess('');
    setFieldErrors({});
  };

  const saveEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    if (!editValues.assigned_city_id) {
      setFieldErrors({ assigned_city_id: text('selectOption') });
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    setFieldErrors({});
    try {
      const { initial_password, assigned_city_id, ...accountChanges } = editValues;
      const updated = await updateManagedBrokerAccount(editing.id, {
        ...accountChanges,
        assigned_city_id: Number(assigned_city_id),
        ...(initial_password ? { initial_password } : {}),
      });
      setAccounts((current) => current.map((item) => item.id === updated.id ? updated : item));
      setEditing(null);
      setSuccess(text('brokerUpdated'));
    } catch (updateError: unknown) {
      setError(getErrorMessage(updateError));
      setFieldErrors(getApiFieldErrors(updateError));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (account: ManagedBrokerAccount) => {
    setError('');
    setSuccess('');
    setUpdatingId(account.id);
    try {
      const updated = await updateManagedBrokerAccount(account.id, { is_active: !account.is_active });
      setAccounts((current) => current.map((item) => item.id === updated.id ? updated : item));
      setSuccess(text('brokerUpdated'));
    } catch (updateError: unknown) {
      setError(getErrorMessage(updateError));
    } finally {
      setUpdatingId(null);
    }
  };

  const removeAccount = async (account: ManagedBrokerAccount) => {
    if (!window.confirm(text('confirmBrokerDelete'))) return;
    setError('');
    setSuccess('');
    setDeletingId(account.id);
    try {
      await deleteManagedBrokerAccount(account.id);
      setAccounts((current) => current.filter((item) => item.id !== account.id));
      if (editing?.id === account.id) setEditing(null);
      setSuccess(text('brokerDeleted'));
    } catch (deleteError: unknown) {
      setError(getErrorMessage(deleteError));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <main className="manager-page" id="main-content">
      <header className="manager-page-header">
        <div>
          <h1>{text('managerBrokerAccounts')}</h1>
          <p>{text('brokerAccountsDescription')}</p>
        </div>
      </header>

      {error && <p className="manager-error" role="alert">{error}</p>}
      {success && <p className="manager-inline-success" role="status">{success}</p>}

      <section className="manager-panel">
        <h2>{text('createBrokerAccount')}</h2>
        <p>{text('brokerInitialPasswordHelp')}</p>
        <form className="manager-form-grid" onSubmit={(event) => void createAccount(event)}>
          <label className="filter-label">{text('brokerUsername')}
            <input
              className="filter-input"
              required
              maxLength={150}
              autoComplete="off"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
            {fieldErrors.username && <small role="alert">{fieldErrors.username}</small>}
          </label>
          <label className="filter-label">{text('initialPassword')}
            <input
              className="filter-input"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {fieldErrors.password && <small role="alert">{fieldErrors.password}</small>}
          </label>
          <label className="filter-label">{text('assignedCity')}
            <select
              className="filter-select"
              required
              value={assignedCityId}
              onChange={(event) => {
                setAssignedCityId(event.target.value);
                setFieldErrors((current) => ({ ...current, assigned_city_id: '' }));
              }}
            >
              <option value="">{text('selectOption')}</option>
              {cities.map((city) => (
                <option key={city.id} value={city.id}>
                  {city.name}
                </option>
              ))}
            </select>
            {fieldErrors.assigned_city_id && <small role="alert">{fieldErrors.assigned_city_id}</small>}
            {cities.length === 0 && <small>{text('locationOptionsEmpty')}</small>}
          </label>
          <div className="location-form-actions">
            <button className="button button-primary" type="submit" disabled={saving || cities.length === 0}>
              {saving ? text('creatingAccount') : text('createBrokerAccount')}
            </button>
          </div>
        </form>
      </section>

      {editing && (
        <section className="manager-panel">
          <h2>{text('editBroker')}</h2>
          <form className="manager-form-grid" onSubmit={(event) => void saveEdit(event)}>
            <label className="filter-label">{text('brokerUsername')}
              <input
                className="filter-input"
                required
                maxLength={150}
                value={editValues.username}
                onChange={(event) => setEditValues((current) => ({ ...current, username: event.target.value }))}
              />
              {fieldErrors.username && <small role="alert">{fieldErrors.username}</small>}
            </label>
            <label className="filter-label">{text('resetBrokerPassword')}
              <input
                className="filter-input"
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={editValues.initial_password}
                onChange={(event) => setEditValues((current) => ({ ...current, initial_password: event.target.value }))}
              />
              <small>{text('brokerPasswordResetHelp')}</small>
              {fieldErrors.initial_password && <small role="alert">{fieldErrors.initial_password}</small>}
            </label>
            <label className="filter-label">{text('assignedCity')}
              <select
                className="filter-select"
                required
                value={editValues.assigned_city_id}
                onChange={(event) => setEditValues((current) => ({ ...current, assigned_city_id: event.target.value }))}
              >
                <option value="">{text('selectOption')}</option>
                {cities.map((city) => (
                  <option key={city.id} value={city.id}>{city.name}</option>
                ))}
              </select>
              {fieldErrors.assigned_city_id && <small role="alert">{fieldErrors.assigned_city_id}</small>}
            </label>
            <label className="filter-label">{text('brokerEmail')}
              <input
                className="filter-input"
                type="email"
                maxLength={254}
                value={editValues.email}
                onChange={(event) => setEditValues((current) => ({ ...current, email: event.target.value }))}
              />
              {fieldErrors.email && <small role="alert">{fieldErrors.email}</small>}
            </label>
            <label className="filter-label">{text('brokerFirstName')}
              <input
                className="filter-input"
                maxLength={150}
                value={editValues.first_name}
                onChange={(event) => setEditValues((current) => ({ ...current, first_name: event.target.value }))}
              />
              {fieldErrors.first_name && <small role="alert">{fieldErrors.first_name}</small>}
            </label>
            <label className="filter-label">{text('brokerLastName')}
              <input
                className="filter-input"
                maxLength={150}
                value={editValues.last_name}
                onChange={(event) => setEditValues((current) => ({ ...current, last_name: event.target.value }))}
              />
              {fieldErrors.last_name && <small role="alert">{fieldErrors.last_name}</small>}
            </label>
            <label className="filter-label">{text('brokerPhone')}
              <input
                className="filter-input"
                maxLength={50}
                value={editValues.phone}
                onChange={(event) => setEditValues((current) => ({ ...current, phone: event.target.value }))}
              />
              {fieldErrors.phone && <small role="alert">{fieldErrors.phone}</small>}
            </label>
            <label className="filter-label">
              <input
                type="checkbox"
                checked={editValues.is_active}
                onChange={(event) => setEditValues((current) => ({ ...current, is_active: event.target.checked }))}
              />
              {' '}{text('brokerAccountActive')}
            </label>
            <div className="location-form-actions">
              <button className="button button-primary" type="submit" disabled={saving}>
                {saving ? text('savingLocation') : text('saveBroker')}
              </button>
              <button className="button button-secondary" type="button" onClick={() => setEditing(null)}>
                {text('cancel')}
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="manager-panel location-list-panel">
        <div className="manager-panel-heading">
          <h2>{text('configuredBrokerAccounts')}</h2>
          <span>{accounts.length}</span>
        </div>
        {loading ? <p role="status">{text('loadingLocations')}</p> : accounts.length === 0 ? (
          <p>{text('brokerAccountsEmpty')}</p>
        ) : (
          <div className="location-table-wrap">
            <table className="manager-table">
              <thead>
                <tr>
                  <th>{text('brokerUsername')}</th>
                  <th>{text('brokerFullName')}</th>
                  <th>{text('brokerEmail')}</th>
                  <th>{text('assignedCity')}</th>
                  <th>{text('listingStatus')}</th>
                  <th>{text('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id}>
                    <td>{account.username}</td>
                    <td>{[account.first_name, account.last_name].filter(Boolean).join(' ') || '—'}</td>
                    <td>{account.email || '—'}</td>
                    <td>{cities.find((city) => city.id === account.assigned_city_id)?.name ?? '—'}</td>
                    <td>
                      {!account.is_active
                        ? text('statusInactive')
                        : account.broker_onboarding_required
                          ? text('brokerSetupPending')
                          : text('brokerSetupComplete')}
                    </td>
                    <td>
                      <div className="location-row-actions">
                        <button className="button button-secondary" type="button" onClick={() => beginEdit(account)}>
                          {text('editBroker')}
                        </button>
                        <button
                          className="button button-secondary"
                          type="button"
                          disabled={updatingId === account.id}
                          onClick={() => void toggleActive(account)}
                        >
                          {text(account.is_active ? 'deactivateBroker' : 'reactivateBroker')}
                        </button>
                        <button
                          className="button button-outline"
                          type="button"
                          disabled={deletingId === account.id}
                          onClick={() => void removeAccount(account)}
                        >
                          {text('deleteBroker')}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
