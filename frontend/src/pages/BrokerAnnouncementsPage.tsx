import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { CalendarDays, Check, ChevronLeft, ChevronRight, Clock3, Eye, MapPin, Search, X } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import {
  decideOwnerAnnouncement,
  getBrokerAnnouncement,
  getBrokerAnnouncements,
  getMarketplaceNotifications,
  markMarketplaceNotificationRead,
  requestBrokerAnnouncementRenewal,
  type BrokerAnnouncementFilters,
  type BrokerAnnouncementQueue,
  type BrokerAnnouncementSummary,
  type MarketplaceNotification,
  type OwnerAnnouncement,
} from '../api/ownerAnnouncements';
import type { PropertyType } from '../api/properties';
import { PropertySlideshow } from '../components/PropertySlideshow';
import { formatPropertyPrice, formatRegistrationDate } from '../components/propertyDisplay';
import { usePreferences } from '../PreferencesContext';
import { messages, type MessageKey } from '../i18n';

const PAGE_SIZE = 12;
const QUEUES: { key: BrokerAnnouncementQueue | 'all'; label: string; countKey?: keyof BrokerAnnouncementSummary }[] = [
  { key: 'all', label: 'All announcements', countKey: 'total' },
  { key: 'pending_review', label: 'Pending review', countKey: 'pending_review' },
  { key: 'approved', label: 'Approved / published', countKey: 'approved' },
  { key: 'changes', label: 'Changes requested', countKey: 'changes' },
  { key: 'renewal_requested', label: 'Renewal requested', countKey: 'renewal_requested' },
  { key: 'expiring_soon', label: 'Expiring soon', countKey: 'expiring_soon' },
  { key: 'expired', label: 'Expired', countKey: 'expired' },
  { key: 'closed', label: 'Rejected / suspended', countKey: 'closed' },
];
const PROPERTY_TYPES: { value: PropertyType; label: string }[] = [
  { value: 'house', label: 'House' },
  { value: 'villa', label: 'Villa' },
  { value: 'apartment', label: 'Apartment' },
  { value: 'condominium', label: 'Condominium' },
  { value: 'land', label: 'Land' },
  { value: 'office', label: 'Office' },
  { value: 'shop', label: 'Shop' },
  { value: 'warehouse', label: 'Warehouse' },
  { value: 'commercial', label: 'Commercial' },
  { value: 'other', label: 'Other' },
];
const QUEUE_KEYS = new Set(QUEUES.filter((queue) => queue.key !== 'all').map((queue) => queue.key));

function asQueue(value: string | null): BrokerAnnouncementQueue | undefined {
  return value && QUEUE_KEYS.has(value as BrokerAnnouncementQueue)
    ? value as BrokerAnnouncementQueue
    : undefined;
}

function localIsoDate(): string {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

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

function statusLabel(status: string): string {
  return status.replaceAll('_', ' ');
}

function announcementOrdering(value: string | null): NonNullable<BrokerAnnouncementFilters['ordering']> {
  const validOrderings: NonNullable<BrokerAnnouncementFilters['ordering']>[] = [
    'submitted_at',
    '-submitted_at',
    'updated_at',
    '-updated_at',
    'property__title',
    '-property__title',
    'active_agreement_end_date',
    '-active_agreement_end_date',
  ];
  return validOrderings.find((ordering) => ordering === value) ?? '-submitted_at';
}

function dateLabel(value: string | null | undefined, locale: 'en' | 'am'): string {
  return formatRegistrationDate(value, locale) ?? '—';
}

function activeAgreement(item: OwnerAnnouncement) {
  return item.agreements.find((agreement) => agreement.status === 'active')
    ?? [...item.agreements].sort((first, second) => second.end_date.localeCompare(first.end_date))[0];
}

function daysUntil(date: string): number {
  const target = new Date(`${date}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / 86_400_000);
}

interface AnnouncementCardProps {
  item: OwnerAnnouncement;
  locale: 'en' | 'am';
  text: (key: MessageKey) => string;
  onOpen: () => void;
  onRenew: () => void;
  busy: boolean;
}

function AnnouncementCard({ item, locale, text, onOpen, onRenew, busy }: AnnouncementCardProps) {
  const agreement = activeAgreement(item);
  const expiryDays = agreement?.status === 'active' ? daysUntil(agreement.end_date) : null;
  const locationPath = item.property.administrative_location_path.join(' · ');
  const location = [locationPath, item.property.location].filter(Boolean).join(' · ');
  const ownerName = item.submitter_name || item.owner_contact_name;
  const submittedDate = formatRegistrationDate(item.submitted_at, locale);

  return (
    <article className="broker-announcement-card">
      <div className="broker-announcement-card-media">
        <PropertySlideshow
          images={item.property.images}
          title={item.property.title}
          fallbackLabel={text('emptyImageLabel')}
          previousLabel={text('previousPage')}
          nextLabel={text('nextPage')}
          photoLabel={text('photoNumber')}
        />
        <span className={`listing-type${item.property.listing_type === 'rent' ? ' is-rent' : ''}`}>
          {item.property.listing_type === 'rent' ? text('forRent') : text('forSale')}
        </span>
      </div>
      <div className="broker-announcement-card-content">
        <div className="broker-announcement-card-heading">
          <div>
            <span className={`announcement-status-badge status-${item.status}`}>{statusLabel(item.status)}</span>
            <h2>{item.property.title}</h2>
          </div>
          <strong className="listing-price">
            {formatPropertyPrice(
              item.property.price,
              item.property.listing_type,
              item.property.rental_frequency as 'daily' | 'weekly' | 'monthly' | 'yearly' | '',
              locale,
              text,
            )}
          </strong>
        </div>
        <div className="broker-announcement-card-meta">
          <span>{statusLabel(item.property.property_type)}</span>
          <span>{item.property.bedrooms} bd · {item.property.bathrooms} ba</span>
          {item.property.area_value && <span>{item.property.area_value} {item.property.area_unit}</span>}
        </div>
        <p className="broker-announcement-location"><MapPin size={15} aria-hidden="true" />{location || 'Location not provided'}</p>
        <div className="broker-announcement-owner">
          <span>Submitted by <strong>{ownerName}</strong></span>
          <span>{submittedDate ? `Submitted ${submittedDate}` : 'Submission date unavailable'}</span>
        </div>
        {agreement && (
          <div className="broker-announcement-agreement">
            <span><CalendarDays size={14} aria-hidden="true" /> Agreement {agreement.start_date} — {agreement.end_date}</span>
            {expiryDays !== null && expiryDays >= 0 && expiryDays <= 30 && (
              <span className="agreement-expiry-warning"><Clock3 size={14} aria-hidden="true" /> Expires in {expiryDays} day{expiryDays === 1 ? '' : 's'}</span>
            )}
            {item.status === 'expired' && <span className="agreement-expiry-warning">Agreement expired</span>}
          </div>
        )}
        <div className="broker-announcement-card-actions">
          {item.status === 'expired' && !item.renewal_requested_at && (
            <button className="button button-outline" type="button" disabled={busy} onClick={onRenew}>
              {busy ? 'Sending…' : 'Request owner renewal'}
            </button>
          )}
          <button className="button button-primary" type="button" onClick={onOpen}>
            <Eye size={16} aria-hidden="true" /> Review details
          </button>
        </div>
      </div>
    </article>
  );
}

interface AnnouncementDetailsProps {
  item: OwnerAnnouncement;
  locale: 'en' | 'am';
  text: (key: MessageKey) => string;
  busy: boolean;
  onClose: () => void;
  onDecision: (decision: Parameters<typeof decideOwnerAnnouncement>[1]) => Promise<void>;
}

function AnnouncementDetails({ item, locale, text, busy, onClose, onDecision }: AnnouncementDetailsProps) {
  const [feedback, setFeedback] = useState('');
  const [startDate, setStartDate] = useState(localIsoDate);
  const [duration, setDuration] = useState(12);
  const [terms, setTerms] = useState('');
  const [renewalConditions, setRenewalConditions] = useState('');
  const [contactVisible, setContactVisible] = useState(false);
  const [exactLocationVisible, setExactLocationVisible] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  const busyRef = useRef(busy);
  onCloseRef.current = onClose;
  busyRef.current = busy;
  const awaitingReview = item.status === 'pending_review' || item.status === 'corrections_requested';
  const renewalReview = ['approved', 'expired'].includes(item.status) && Boolean(item.renewal_requested_at);
  const canApprove = awaitingReview || renewalReview;
  const agreement = activeAgreement(item);

  useEffect(() => {
    const returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialogRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busyRef.current) {
        onCloseRef.current();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      returnFocus?.focus();
    };
  }, []);

  const approve = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    return onDecision({
      action: 'approve',
      confirm_summary: confirmed,
      agreement_start_date: startDate,
      agreement_end_date: addMonthsMinusOneDay(startDate, duration),
      duration_months: duration,
      agreement_terms: terms,
      renewal_conditions: renewalConditions,
      public_contact_visible: contactVisible,
      public_contact_name: item.owner_contact_name,
      public_contact_phone: item.owner_contact_phone,
      public_contact_email: item.owner_contact_email,
      exact_location_is_public: exactLocationVisible,
    });
  };

  const feedbackDecision = (action: 'request_corrections' | 'reject' | 'suspend') => {
    void onDecision({ action, feedback });
  };

  return (
    <div className="broker-announcement-dialog-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !busy) onClose();
    }}>
      <section
        className="broker-announcement-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="announcement-details-title"
        tabIndex={-1}
        ref={dialogRef}
      >
        <header className="broker-announcement-dialog-header">
          <div>
            <span className={`announcement-status-badge status-${item.status}`}>{statusLabel(item.status)}</span>
            <h2 id="announcement-details-title">{item.property.title}</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Close details" onClick={onClose} disabled={busy}>
            <X size={20} aria-hidden="true" />
          </button>
        </header>
        <div className="broker-announcement-dialog-body">
          <div className="broker-announcement-detail-grid">
            <div>
              <h3>Property</h3>
              <p>{item.property.property_type} · {item.property.listing_type === 'rent' ? 'For rent' : 'For sale'}</p>
              <p>{formatPropertyPrice(
                item.property.price,
                item.property.listing_type,
                item.property.rental_frequency as 'daily' | 'weekly' | 'monthly' | 'yearly' | '',
                locale,
                text,
              )}</p>
              <p><MapPin size={15} aria-hidden="true" /> {[...item.property.administrative_location_path, item.property.location].filter(Boolean).join(' · ')}</p>
              <p>{item.property.bedrooms} bedrooms · {item.property.bathrooms} bathrooms · {item.property.area_value || item.property.area_sqft} {item.property.area_unit || 'sq ft'}</p>
              <p className="announcement-detail-description">{item.property.description}</p>
              {item.property.features && <p><strong>Features:</strong> {item.property.features}</p>}
            </div>
            <div>
              <h3>Owner and submission</h3>
              <p><strong>Submitter:</strong> {item.submitter_name || item.owner_contact_name}</p>
              <p><strong>Private owner contact:</strong> {item.owner_contact_name}</p>
              <p><strong>Phone:</strong> <a href={`tel:${item.owner_contact_phone}`}>{item.owner_contact_phone}</a></p>
              {item.owner_contact_email && <p><strong>Email:</strong> <a href={`mailto:${item.owner_contact_email}`}>{item.owner_contact_email}</a></p>}
              <p><strong>Submitted:</strong> {dateLabel(item.submitted_at, locale)}</p>
              <p><strong>Publication:</strong> {statusLabel(item.property.publication_status)}</p>
              {item.broker_feedback && <p className="auth-form-error"><strong>Previous review:</strong> {item.broker_feedback}</p>}
            </div>
          </div>
          {agreement && (
            <section className="broker-agreement-detail">
              <h3>Agreement</h3>
              <p>{agreement.start_date} — {agreement.end_date} · {agreement.duration_months} months · {statusLabel(agreement.status)}</p>
              <p>{agreement.terms}</p>
              {agreement.renewal_conditions && <p><strong>Renewal conditions:</strong> {agreement.renewal_conditions}</p>}
              <p>Owner renewal requested: {item.renewal_requested_at ? dateLabel(item.renewal_requested_at, locale) : 'No'}</p>
            </section>
          )}
          {(awaitingReview || renewalReview || item.status === 'approved') && (
            <section className="broker-decision-panel">
              <h3>{canApprove ? 'Review decision' : 'Publication controls'}</h3>
              {canApprove && (
                <form className="auth-form broker-agreement-form" onSubmit={(event) => void approve(event)}>
                  <div className="search-fields">
                    <label className="search-field">Agreement start date
                      <input type="date" required value={startDate} onChange={(event) => setStartDate(event.target.value)} />
                    </label>
                    <label className="search-field">Duration (months)
                      <input type="number" min="1" max="120" required value={duration} onChange={(event) => setDuration(Number(event.target.value))} />
                    </label>
                  </div>
                  <p>Calculated agreement expiry: <strong>{addMonthsMinusOneDay(startDate, duration)}</strong></p>
                  <label>Agreement terms *
                    <textarea required maxLength={4000} rows={3} value={terms} onChange={(event) => setTerms(event.target.value)} />
                  </label>
                  <label>Renewal conditions
                    <textarea maxLength={2000} rows={2} value={renewalConditions} onChange={(event) => setRenewalConditions(event.target.value)} />
                  </label>
                  <label className="checkbox-field">
                    <input type="checkbox" checked={contactVisible} onChange={(event) => setContactVisible(event.target.checked)} />
                    Display owner contact details publicly
                  </label>
                  <label className="checkbox-field">
                    <input type="checkbox" checked={exactLocationVisible} onChange={(event) => setExactLocationVisible(event.target.checked)} />
                    Display exact property coordinates publicly
                  </label>
                  <label className="checkbox-field">
                    <input type="checkbox" required checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
                    I reviewed and confirm the agreement and public-contact choices.
                  </label>
                  <button className="button button-primary" type="submit" disabled={busy}>
                    <Check size={16} aria-hidden="true" /> Approve with agreement
                  </button>
                </form>
              )}
              {(awaitingReview || item.status === 'approved') && (
                <div className="broker-decision-secondary">
                  {awaitingReview && (
                    <>
                      <label>Reason for corrections or rejection
                        <textarea rows={2} value={feedback} onChange={(event) => setFeedback(event.target.value)} />
                      </label>
                      <button className="button button-outline" type="button" disabled={busy || !feedback.trim()} onClick={() => feedbackDecision('request_corrections')}>
                        Request corrections
                      </button>
                      <button className="button button-outline button-danger" type="button" disabled={busy || !feedback.trim()} onClick={() => feedbackDecision('reject')}>
                        Reject announcement
                      </button>
                    </>
                  )}
                  {item.status === 'approved' && (
                    <>
                      <label>Reason for suspension
                        <textarea rows={2} value={feedback} onChange={(event) => setFeedback(event.target.value)} />
                      </label>
                      <button className="button button-outline button-danger" type="button" disabled={busy || !feedback.trim()} onClick={() => feedbackDecision('suspend')}>
                        Suspend public listing
                      </button>
                    </>
                  )}
                </div>
              )}
              {item.status === 'expired' && !item.renewal_requested_at && (
                <p>An expired listing is not republished automatically. Request a new owner agreement from the card or wait for the owner to submit renewal.</p>
              )}
            </section>
          )}
        </div>
      </section>
    </div>
  );
}

export function BrokerAnnouncementsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { preferences } = usePreferences();
  const locale = preferences.locale;
  const text = (key: MessageKey) => messages[locale][key];
  const queue = asQueue(searchParams.get('queue'));
  const searchTerm = searchParams.get('search') ?? '';
  const propertyType = searchParams.get('property_type') ?? '';
  const listingType = searchParams.get('listing_type') ?? '';
  const publicationStatus = searchParams.get('publication_status') ?? '';
  const location = searchParams.get('location') ?? '';
  const ordering = announcementOrdering(searchParams.get('ordering'));
  const currentPage = Math.max(1, Number(searchParams.get('page') || '1') || 1);
  const detailsId = Number(searchParams.get('announcement')) || null;
  const [searchInput, setSearchInput] = useState(searchTerm);
  const [locationInput, setLocationInput] = useState(location);
  const [items, setItems] = useState<OwnerAnnouncement[]>([]);
  const [summary, setSummary] = useState<BrokerAnnouncementSummary | null>(null);
  const [notifications, setNotifications] = useState<MarketplaceNotification[]>([]);
  const [selected, setSelected] = useState<OwnerAnnouncement | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => setSearchInput(searchTerm), [searchTerm]);
  useEffect(() => setLocationInput(location), [location]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        if (searchInput.trim()) next.set('search', searchInput.trim());
        else next.delete('search');
        if (next.get('search') !== current.get('search')) next.delete('page');
        return next.toString() === current.toString() ? current : next;
      }, { replace: true });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput, setSearchParams]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        if (locationInput.trim()) next.set('location', locationInput.trim());
        else next.delete('location');
        if (next.get('location') !== current.get('location')) next.delete('page');
        return next.toString() === current.toString() ? current : next;
      }, { replace: true });
    }, 350);
    return () => window.clearTimeout(timer);
  }, [locationInput, setSearchParams]);

  const filters = useMemo<BrokerAnnouncementFilters>(() => ({
    ...(queue ? { queue } : {}),
    ...(searchTerm ? { search: searchTerm } : {}),
    ...(propertyType ? { property_type: propertyType } : {}),
    ...(listingType === 'rent' || listingType === 'sale' ? { listing_type: listingType } : {}),
    ...(publicationStatus ? { publication_status: publicationStatus } : {}),
    ...(location ? { location } : {}),
    ordering,
    page: currentPage,
    page_size: PAGE_SIZE,
  }), [currentPage, listingType, location, ordering, propertyType, publicationStatus, queue, searchTerm]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setListLoading(true);
      setError('');
      getBrokerAnnouncements(filters, controller.signal)
        .then((response) => {
          setItems(response.results);
          setCount(response.count);
          setHasNext(Boolean(response.next));
          setHasPrevious(Boolean(response.previous));
          setSummary(response.summary);
        })
        .catch((requestError: unknown) => {
          if (!controller.signal.aborted) setError(getErrorMessage(requestError));
        })
        .finally(() => {
          if (!controller.signal.aborted) setListLoading(false);
        });
    }, filters.search || filters.location ? 250 : 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [filters, refreshKey]);

  useEffect(() => {
    const controller = new AbortController();
    getMarketplaceNotifications(controller.signal)
      .then((response) => setNotifications(response.results))
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) setError(getErrorMessage(requestError));
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!detailsId) {
      setSelected(null);
      setDetailLoading(false);
      return;
    }
    const visibleItem = items.find((item) => item.id === detailsId);
    if (visibleItem) {
      setSelected(visibleItem);
      setDetailLoading(false);
      return;
    }
    if (listLoading) return;
    const controller = new AbortController();
    setDetailLoading(true);
    getBrokerAnnouncement(detailsId, controller.signal)
      .then(setSelected)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) setError(getErrorMessage(requestError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setDetailLoading(false);
      });
    return () => controller.abort();
  }, [detailsId, items, listLoading]);

  const updateQuery = (key: string, value: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== 'announcement') next.delete('page');
    setSearchParams(next);
  };

  const closeDetails = () => updateQuery('announcement', null);

  const markRead = async (notification: MarketplaceNotification) => {
    try {
      const updated = await markMarketplaceNotificationRead(notification.id);
      setNotifications((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    }
  };

  const requestRenewal = async (item: OwnerAnnouncement) => {
    setBusyId(item.id);
    setError('');
    setNotice('');
    try {
      await requestBrokerAnnouncementRenewal(item.id);
      setNotice(`A new agreement discussion was requested from ${item.submitter_name || item.owner_contact_name}.`);
      setRefreshKey((current) => current + 1);
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  const decide = async (item: OwnerAnnouncement, decision: Parameters<typeof decideOwnerAnnouncement>[1]) => {
    setBusyId(item.id);
    setError('');
    setNotice('');
    try {
      await decideOwnerAnnouncement(item.id, decision);
      setNotice('Review decision saved.');
      closeDetails();
      setRefreshKey((current) => current + 1);
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  const changePage = (page: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page));
    setSearchParams(next);
  };

  const startResult = count ? (currentPage - 1) * PAGE_SIZE + 1 : 0;
  const endResult = Math.min(currentPage * PAGE_SIZE, count);

  return (
    <main className="management-page broker-announcements-page" id="main-content">
      <div className="container">
        <header className="section-heading broker-announcement-page-heading">
          <div>
            <p className="eyebrow eyebrow-muted">Broker workspace</p>
            <h1>Owner announcements</h1>
            <p className="section-description">Review submissions, manage publication, and track agreement dates.</p>
          </div>
        </header>
        {error && <p className="auth-form-error" role="alert">{error}</p>}
        {notice && <p className="form-success" role="status">{notice}</p>}

        {notifications.length > 0 && (
          <section className="broker-notification-strip" aria-label="Broker notifications">
            {notifications.slice(0, 3).map((notification) => (
              <article className="broker-notification-item" key={notification.id}>
                <p>{notification.message}</p>
                {!notification.read_at && (
                  <button className="button button-outline" type="button" onClick={() => void markRead(notification)}>
                    Mark as read
                  </button>
                )}
              </article>
            ))}
          </section>
        )}

        <section className="broker-announcement-queues" aria-label="Announcement queues">
          {QUEUES.map(({ key, label, countKey }) => (
            <button
              className={`broker-announcement-queue${(queue ?? 'all') === key ? ' is-active' : ''}`}
              key={key}
              type="button"
              aria-pressed={(queue ?? 'all') === key}
              onClick={() => updateQuery('queue', key === 'all' ? null : key)}
            >
              <span>{label}</span>
              <strong>{countKey ? summary?.[countKey] ?? '—' : '—'}</strong>
            </button>
          ))}
        </section>

        <section className="broker-announcement-toolbar" aria-label="Search and filters">
          <label className="broker-announcement-search">
            <Search size={17} aria-hidden="true" />
            <span className="visually-hidden">Search title, ID, owner or submitter</span>
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search title, ID, owner or submitter"
            />
          </label>
          <label>
            <span className="visually-hidden">Filter by location</span>
            <input
              type="search"
              value={locationInput}
              onChange={(event) => setLocationInput(event.target.value)}
              placeholder="Location"
            />
          </label>
          <label>
            <span className="visually-hidden">Filter by property type</span>
            <select value={propertyType} onChange={(event) => updateQuery('property_type', event.target.value || null)}>
              <option value="">All property types</option>
              {PROPERTY_TYPES.map((type) => <option value={type.value} key={type.value}>{type.label}</option>)}
            </select>
          </label>
          <label>
            <span className="visually-hidden">Filter by listing type</span>
            <select value={listingType} onChange={(event) => updateQuery('listing_type', event.target.value || null)}>
              <option value="">Rent and sale</option>
              <option value="rent">For rent</option>
              <option value="sale">For sale</option>
            </select>
          </label>
          <label>
            <span className="visually-hidden">Filter by publication status</span>
            <select value={publicationStatus} onChange={(event) => updateQuery('publication_status', event.target.value || null)}>
              <option value="">All publication statuses</option>
              <option value="pending_review">Pending review</option>
              <option value="published">Published</option>
              <option value="rejected">Rejected</option>
              <option value="suspended">Suspended</option>
              <option value="expired">Expired</option>
              <option value="withdrawn">Withdrawn</option>
            </select>
          </label>
          <label>
            <span className="visually-hidden">Sort announcements</span>
            <select value={ordering} onChange={(event) => updateQuery('ordering', event.target.value)}>
              <option value="-submitted_at">Newest submitted</option>
              <option value="submitted_at">Oldest submitted</option>
              <option value="property__title">Property title A–Z</option>
              <option value="-active_agreement_end_date">Expiry: latest first</option>
              <option value="active_agreement_end_date">Expiry: soonest first</option>
            </select>
          </label>
        </section>

        {listLoading ? (
          <p className="broker-announcement-loading" role="status">Loading owner announcements…</p>
        ) : items.length === 0 ? (
          <div className="broker-announcement-empty">
            <h2>No announcements in this view</h2>
            <p>Try another queue or adjust your search and filters.</p>
          </div>
        ) : (
          <section className="broker-announcement-grid" aria-label="Owner announcements">
            {items.map((item) => (
              <AnnouncementCard
                key={item.id}
                item={item}
                locale={locale}
                text={text}
                busy={busyId === item.id}
                onOpen={() => updateQuery('announcement', String(item.id))}
                onRenew={() => void requestRenewal(item)}
              />
            ))}
          </section>
        )}

        <nav className="broker-announcement-pagination" aria-label="Announcement pages">
          <span>{count ? `Showing ${startResult}–${endResult} of ${count}` : '0 announcements'}</span>
          <div>
            <button className="button button-outline" type="button" disabled={!hasPrevious || listLoading} onClick={() => changePage(currentPage - 1)}>
              <ChevronLeft size={16} aria-hidden="true" /> Previous
            </button>
            <span>Page {currentPage}</span>
            <button className="button button-outline" type="button" disabled={!hasNext || listLoading} onClick={() => changePage(currentPage + 1)}>
              Next <ChevronRight size={16} aria-hidden="true" />
            </button>
          </div>
        </nav>

        {detailsId && detailLoading && <div className="broker-announcement-dialog-backdrop"><p role="status">Loading announcement details…</p></div>}
        {detailsId && selected && (
          <AnnouncementDetails
            item={selected}
            locale={locale}
            text={text}
            busy={busyId === selected.id}
            onClose={closeDetails}
            onDecision={(decision) => decide(selected, decision)}
          />
        )}
      </div>
    </main>
  );
}
