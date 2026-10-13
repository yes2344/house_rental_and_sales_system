import { useEffect, useState, type FormEvent } from 'react';
import { getApiFieldErrors, getErrorMessage } from '../api/client';
import {
  createManagedBrokerInvitation,
  getManagedBrokerAccounts,
  updateManagedBrokerAccount,
  type BrokerInvitationResult,
  type ManagedBrokerAccount,
} from '../api/management';
import type { Locale, MessageKey } from '../i18n';

interface BrokerAccountManagementPageProps {
  locale: Locale;
  text: (key: MessageKey) => string;
}

export function BrokerAccountManagementPage({ locale, text }: BrokerAccountManagementPageProps) {
  const [accounts, setAccounts] = useState<ManagedBrokerAccount[]>([]);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [invitation, setInvitation] = useState<BrokerInvitationResult | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getManagedBrokerAccounts(controller.signal)
      .then(setAccounts)
      .catch((loadError: unknown) => {
        if (!controller.signal.aborted) setError(getErrorMessage(loadError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const createInvitation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setFieldErrors({});
    setInvitation(null);
    try {
      const result = await createManagedBrokerInvitation({ username: username.trim(), email: email.trim() });
      setInvitation(result);
      setUsername('');
      setEmail('');
      setAccounts((current) => [...current, result.account].sort((a, b) => a.username.localeCompare(b.username)));
    } catch (createError: unknown) {
      setError(getErrorMessage(createError));
      setFieldErrors(getApiFieldErrors(createError));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (account: ManagedBrokerAccount) => {
    setError('');
    setUpdatingId(account.id);
    try {
      const updated = await updateManagedBrokerAccount(account.id, { is_active: !account.is_active });
      setAccounts((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (updateError: unknown) {
      setError(getErrorMessage(updateError));
    } finally {
      setUpdatingId(null);
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
      {invitation && (
        <section className="manager-panel" role="status">
          <h2>{text('brokerInvitationCreated')}</h2>
          <p>{text('brokerInvitationNotice')}</p>
          <label className="filter-label">{text('brokerInvitationToken')}
            <textarea className="filter-input" readOnly rows={3} value={invitation.invitation_token} />
          </label>
          <p>{text('brokerInvitationExpires')}: {new Date(invitation.invitation_expires_at).toLocaleString(locale === 'am' ? 'am-ET' : 'en-ET')}</p>
        </section>
      )}

      <section className="manager-panel">
        <h2>{text('inviteBroker')}</h2>
        <form className="manager-form-grid" onSubmit={createInvitation}>
          <label className="filter-label">{text('brokerUsername')}
            <input className="filter-input" required maxLength={150} autoComplete="off" value={username} onChange={(event) => setUsername(event.target.value)} />
            {fieldErrors.username && <small role="alert">{fieldErrors.username}</small>}
          </label>
          <label className="filter-label">{text('brokerEmail')}
            <input className="filter-input" required type="email" maxLength={254} autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
            {fieldErrors.email && <small role="alert">{fieldErrors.email}</small>}
          </label>
          <div className="location-form-actions">
            <button className="button button-primary" type="submit" disabled={saving}>
              {saving ? text('savingLocation') : text('createBrokerInvitation')}
            </button>
          </div>
        </form>
      </section>

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
                  <th>{text('brokerEmail')}</th>
                  <th>{text('listingStatus')}</th>
                  <th>{text('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id}>
                    <td>{account.username}</td>
                    <td>{account.email}</td>
                    <td>{text(account.is_active ? 'available' : 'statusInactive')}</td>
                    <td>
                      <button
                        className="button button-secondary"
                        type="button"
                        disabled={updatingId === account.id}
                        onClick={() => void toggleActive(account)}
                      >
                        {text(account.is_active ? 'deactivateBroker' : 'reactivateBroker')}
                      </button>
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
