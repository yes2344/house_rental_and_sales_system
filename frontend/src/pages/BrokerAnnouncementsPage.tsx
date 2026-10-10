import { useEffect, useState, type FormEvent } from 'react';
import { Check, Eye, X } from 'lucide-react';

import { getErrorMessage } from '../api/client';
import {
  decideOwnerAnnouncement,
  getBrokerAnnouncements,
  getMarketplaceNotifications,
  markMarketplaceNotificationRead,
  type MarketplaceNotification,
  type OwnerAnnouncement,
} from '../api/ownerAnnouncements';

function addMonthsMinusOneDay(isoDate: string, months: number): string {
  const [year, month, day] = isoDate.split('-').map(Number);
  const targetMonth = month - 1 + months;
  const targetYear = year + Math.floor(targetMonth / 12);
  const normalizedMonth = targetMonth % 12;
  const monthLastDay = new Date(targetYear, normalizedMonth + 1, 0).getDate();
  const end = new Date(targetYear, normalizedMonth, Math.min(day, monthLastDay));
  end.setDate(end.getDate() - 1);
  return `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, '0')}-${String(end.getDate()).padStart(2, '0')}`;
}

export function BrokerAnnouncementsPage() {
  const [items, setItems] = useState<OwnerAnnouncement[]>([]);
  const [notifications, setNotifications] = useState<MarketplaceNotification[]>([]);
  const [feedback, setFeedback] = useState<Record<number, string>>({});
  const [startDates, setStartDates] = useState<Record<number, string>>({});
  const [durations, setDurations] = useState<Record<number, number>>({});
  const [terms, setTerms] = useState<Record<number, string>>({});
  const [renewalConditions, setRenewalConditions] = useState<Record<number, string>>({});
  const [contactVisible, setContactVisible] = useState<Record<number, boolean>>({});
  const [exactLocationVisible, setExactLocationVisible] = useState<Record<number, boolean>>({});
  const [confirmations, setConfirmations] = useState<Record<number, boolean>>({});
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = async (signal?: AbortSignal) => {
    const [response, notificationResponse] = await Promise.allSettled([
      getBrokerAnnouncements(signal),
      getMarketplaceNotifications(signal),
    ]);
    if (response.status === 'rejected') throw response.reason;
    setItems(response.value.results);
    if (notificationResponse.status === 'fulfilled') {
      setNotifications(notificationResponse.value.results);
    } else {
      setError(getErrorMessage(notificationResponse.reason));
    }
  };

  const markRead = async (notification: MarketplaceNotification) => {
    try {
      const updated = await markMarketplaceNotificationRead(notification.id);
      setNotifications((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).catch((requestError: unknown) => {
      if (!controller.signal.aborted) setError(getErrorMessage(requestError));
    });
    return () => controller.abort();
  }, []);

  const decide = async (item: OwnerAnnouncement, action: 'request_corrections' | 'reject' | 'suspend') => {
    setBusyId(item.id);
    setError('');
    setNotice('');
    try {
      await decideOwnerAnnouncement(item.id, { action, feedback: feedback[item.id] ?? '' });
      setNotice('Review decision saved.');
      await load();
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  const approve = async (event: FormEvent<HTMLFormElement>, item: OwnerAnnouncement) => {
    event.preventDefault();
    const start = startDates[item.id] || new Date().toISOString().slice(0, 10);
    const duration = durations[item.id] ?? 12;
    setBusyId(item.id);
    setError('');
    setNotice('');
    try {
      await decideOwnerAnnouncement(item.id, {
        action: 'approve',
        confirm_summary: confirmations[item.id] ?? false,
        agreement_start_date: start,
        agreement_end_date: addMonthsMinusOneDay(start, duration),
        duration_months: duration,
        agreement_terms: terms[item.id] ?? '',
        renewal_conditions: renewalConditions[item.id] ?? '',
        public_contact_visible: contactVisible[item.id] ?? false,
        public_contact_name: item.owner_contact_name,
        public_contact_phone: item.owner_contact_phone,
        public_contact_email: item.owner_contact_email,
        exact_location_is_public: exactLocationVisible[item.id] ?? false,
      });
      setNotice('Announcement approved under the entered agreement.');
      await load();
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <main className="management-page" id="main-content">
      <div className="container">
        <header className="section-heading">
          <div>
            <p className="eyebrow eyebrow-muted">Broker workspace</p>
            <h1>Owner announcements</h1>
            <p className="section-description">Review owner submissions, record a listing agreement, and control public visibility.</p>
          </div>
        </header>
        {error && <p className="auth-form-error" role="alert">{error}</p>}
        {notice && <p className="form-success" role="status">{notice}</p>}
        {notifications.length > 0 && (
          <section className="section">
            <h2>Notifications</h2>
            <div className="owner-announcement-list">
              {notifications.map((notification) => (
                <article className="auth-card owner-announcement-card" key={notification.id}>
                  <p>{notification.message}</p>
                  {!notification.read_at && (
                    <button className="button button-outline" type="button" onClick={() => void markRead(notification)}>
                      Mark as read
                    </button>
                  )}
                </article>
              ))}
            </div>
          </section>
        )}
        {!items.length ? <p>No owner announcements are awaiting review.</p> : (
          <div className="owner-announcement-list">
            {items.map((item) => {
              const duration = durations[item.id] ?? 12;
              const startDate = startDates[item.id] ?? new Date().toISOString().slice(0, 10);
              const awaitingReview = ['pending_review', 'corrections_requested'].includes(item.status);
              const renewalReview = ['approved', 'expired'].includes(item.status) && Boolean(item.renewal_requested_at);
              return (
                <article className="auth-card owner-announcement-card" key={item.id}>
                  <div>
                    <p className="eyebrow eyebrow-muted">{item.status.replaceAll('_', ' ')}</p>
                    <h2>{item.property.title}</h2>
                    <p>{item.property.location}{item.property.administrative_location_name && ` · ${item.property.administrative_location_name}`}</p>
                    <p>{item.property.listing_type} · {item.property.property_type} · ETB {item.property.price}</p>
                    <p>{item.property.description}</p>
                    <p>Owner contact (private): {item.owner_contact_name} · {item.owner_contact_phone} {item.owner_contact_email}</p>
                    <div className="owner-announcement-images">
                      {item.property.images.map((image) => image.url && (
                        <img key={image.id} src={image.url} alt={image.caption || item.property.title} loading="lazy" />
                      ))}
                    </div>
                    <label>Review notes / decision reason
                      <textarea
                        rows={3}
                        value={feedback[item.id] ?? ''}
                        onChange={(event) => setFeedback((current) => ({ ...current, [item.id]: event.target.value }))}
                      />
                    </label>
                    {awaitingReview || renewalReview ? (
                      <>
                        <form className="auth-form" onSubmit={(event) => void approve(event, item)}>
                          <h3>Agreement and publication</h3>
                          <div className="search-fields">
                            <label className="search-field">Agreement start
                              <input type="date" required value={startDate} onChange={(event) => setStartDates((current) => ({ ...current, [item.id]: event.target.value }))} />
                            </label>
                            <label className="search-field">Duration in months
                              <input type="number" min="1" max="120" required value={duration} onChange={(event) => setDurations((current) => ({ ...current, [item.id]: Number(event.target.value) }))} />
                            </label>
                          </div>
                          <p>Agreement end date: {addMonthsMinusOneDay(startDate, duration)}</p>
                          <label>Agreement terms *
                            <textarea required maxLength={4000} value={terms[item.id] ?? ''} onChange={(event) => setTerms((current) => ({ ...current, [item.id]: event.target.value }))} />
                          </label>
                          <label>Renewal conditions
                            <textarea maxLength={2000} value={renewalConditions[item.id] ?? ''} onChange={(event) => setRenewalConditions((current) => ({ ...current, [item.id]: event.target.value }))} />
                          </label>
                          <label className="checkbox-field">
                            <input type="checkbox" checked={contactVisible[item.id] ?? false} onChange={(event) => setContactVisible((current) => ({ ...current, [item.id]: event.target.checked }))} />
                            Display owner contact details publicly
                          </label>
                          <label className="checkbox-field">
                            <input type="checkbox" checked={exactLocationVisible[item.id] ?? false} onChange={(event) => setExactLocationVisible((current) => ({ ...current, [item.id]: event.target.checked }))} />
                            Display exact property coordinates publicly
                          </label>
                          <label className="checkbox-field">
                            <input type="checkbox" required checked={confirmations[item.id] ?? false} onChange={(event) => setConfirmations((current) => ({ ...current, [item.id]: event.target.checked }))} />
                            I reviewed and confirm the agreement and public-contact choices.
                          </label>
                          <button className="button button-primary" type="submit" disabled={busyId === item.id}>
                            <Check size={16} aria-hidden="true" /> Approve and publish
                          </button>
                        </form>
                        {awaitingReview && (
                          <div className="form-actions">
                            <button className="button button-outline" type="button" disabled={busyId === item.id} onClick={() => void decide(item, 'request_corrections')}>
                              Request corrections
                            </button>
                            <button className="button button-outline" type="button" disabled={busyId === item.id} onClick={() => void decide(item, 'reject')}>
                              <X size={16} aria-hidden="true" /> Reject
                            </button>
                          </div>
                        )}
                      </>
                    ) : item.status === 'approved' ? (
                      <button className="button button-outline" type="button" disabled={busyId === item.id} onClick={() => void decide(item, 'suspend')}>
                        <Eye size={16} aria-hidden="true" /> Suspend public listing
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
