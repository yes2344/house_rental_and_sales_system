import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, CalendarClock, RotateCw, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import {
  cancelCustomerViewingRequest,
  deleteCustomerViewingRequest,
  getCustomerViewingRequests,
  respondToCustomerViewingRequest,
  type CustomerViewingRequest,
  type ViewingRequestStatusValue,
} from '../api/viewings';
import type { Locale, MessageKey } from '../i18n';

interface CustomerViewingRequestsPageProps {
  locale: Locale;
  text: (key: MessageKey) => string;
}

const statuses: ViewingRequestStatusValue[] = [
  'pending', 'proposed', 'confirmed', 'rejected', 'declined', 'cancelled', 'completed',
];

function statusMessage(status: ViewingRequestStatusValue): MessageKey {
  const messages: Record<ViewingRequestStatusValue, MessageKey> = {
    pending: 'viewingPending',
    proposed: 'viewingProposed',
    confirmed: 'viewingConfirmed',
    rejected: 'viewingRejected',
    declined: 'viewingVisitorDeclined',
    cancelled: 'viewingCancelled',
    completed: 'viewingCompleted',
  };
  return messages[status];
}

function eventMessage(eventType: string): MessageKey {
  if (eventType === 'proposal_sent') return 'appointmentProposedEvent';
  if (eventType === 'proposal_revised') return 'appointmentRevisedEvent';
  if (eventType === 'proposal_accepted') return 'appointmentAcceptedEvent';
  if (eventType === 'proposal_declined') return 'appointmentDeclinedEvent';
  if (eventType === 'request_confirmed') return 'requestConfirmedEvent';
  if (eventType === 'rejected') return 'requestRejectedEvent';
  if (eventType === 'cancelled') return 'viewingCancelled';
  if (eventType === 'completed') return 'viewingCompleted';
  return 'requestSubmittedEvent';
}

function formatDate(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale === 'am' ? 'am-ET' : 'en-ET', {
    dateStyle: 'medium',
  }).format(new Date(`${value}T00:00:00`));
}

export function CustomerViewingRequestsPage({ locale, text }: CustomerViewingRequestsPageProps) {
  const [requests, setRequests] = useState<CustomerViewingRequest[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [busyRequest, setBusyRequest] = useState<number | null>(null);
  const [reload, setReload] = useState(0);

  const loadRequests = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await getCustomerViewingRequests(
        page,
        statusFilter ? statusFilter as ViewingRequestStatusValue : undefined,
      );
      setRequests(result.results);
      setCount(result.count);
      setHasPrevious(Boolean(result.previous));
      setHasNext(Boolean(result.next));
    } catch (loadError: unknown) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [page, reload, statusFilter]);

  useEffect(() => {
    void loadRequests();
  }, [loadRequests]);

  const runAction = async (
    request: CustomerViewingRequest,
    action: 'accept' | 'decline' | 'cancel',
  ) => {
    setBusyRequest(request.id);
    setActionError('');
    try {
      if (action === 'cancel') await cancelCustomerViewingRequest(request.id);
      else await respondToCustomerViewingRequest(request.id, action);
      await loadRequests();
    } catch (actionFailure: unknown) {
      setActionError(getErrorMessage(actionFailure));
    } finally {
      setBusyRequest(null);
    }
  };

  const deleteCancelledRequest = async (request: CustomerViewingRequest) => {
    if (!window.confirm(text('confirmDeleteCancelledRequest'))) return;
    setBusyRequest(request.id);
    setActionError('');
    try {
      await deleteCustomerViewingRequest(request.id);
      if (requests.length === 1 && page > 1) {
        setPage((current) => current - 1);
      } else {
        await loadRequests();
      }
    } catch (actionFailure: unknown) {
      setActionError(getErrorMessage(actionFailure));
    } finally {
      setBusyRequest(null);
    }
  };

  const changeFilter = (value: string) => {
    setStatusFilter(value);
    setPage(1);
  };

  return (
    <main id="main-content" className="customer-page">
      <section className="customer-heading">
        <div className="container">
          <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text('viewingActivity')}</p>
          <h1>{text('yourViewingRequests')}</h1>
          <p>{text('yourViewingRequestsIntro')}</p>
        </div>
      </section>
      <section className="container customer-content">
        <section className="customer-panel" aria-labelledby="customer-viewing-requests-title">
          <div className="customer-panel-heading">
            <div>
              <h2 id="customer-viewing-requests-title">{text('viewingActivity')}</h2>
              <p>{text('yourViewingRequestsCount').replace('{count}', String(count))}</p>
            </div>
            <div className="customer-request-toolbar">
              <label>
                <span className="visually-hidden">{text('requestStatus')}</span>
                <select value={statusFilter} onChange={(event) => changeFilter(event.target.value)}>
                  <option value="">{text('allStatuses')}</option>
                  {statuses.map((status) => (
                    <option key={status} value={status}>{text(statusMessage(status))}</option>
                  ))}
                </select>
              </label>
              <button className="button button-outline button-small" type="button" onClick={() => setReload((value) => value + 1)}>
                <RotateCw size={15} aria-hidden="true" />{text('refresh')}
              </button>
            </div>
          </div>

          {error && <div className="customer-error" role="alert"><p>{text('activityLoadError')} {error}</p></div>}
          {actionError && <div className="customer-error" role="alert"><p>{actionError}</p></div>}
          {loading ? (
            <div className="listing-state" role="status"><span className="loading-spinner" />{text('loadingActivity')}</div>
          ) : requests.length ? (
            <div className="customer-request-list">
              {requests.map((request) => (
                <article className="customer-request-card" key={request.id}>
                  <div className="customer-request-heading">
                    <div>
                      <Link to={`/properties/${encodeURIComponent(request.property.slug)}`}>{request.property.title}</Link>
                      <p>{request.property.location}</p>
                    </div>
                    <span className={`activity-status is-${request.status}`}>{text(statusMessage(request.status))}</span>
                  </div>
                  <div className="customer-request-dates">
                    <p><strong>{text('preferredDate')}:</strong> {formatDate(request.preferred_date, locale)}{request.preferred_time ? ` · ${request.preferred_time.slice(0, 5)}` : ''}</p>
                    {request.proposed_date && request.status === 'proposed' && (
                      <p><strong>{text('appointmentProposalDate')}:</strong> {formatDate(request.proposed_date, locale)}{request.proposed_time ? ` · ${request.proposed_time.slice(0, 5)}` : ''}</p>
                    )}
                    {request.scheduled_date && (
                      <p><strong>{text('scheduledDate')}:</strong> {formatDate(request.scheduled_date, locale)}{request.scheduled_time ? ` · ${request.scheduled_time.slice(0, 5)}` : ''} ({request.appointment_timezone})</p>
                    )}
                  </div>
                  {request.message && <p className="customer-request-message">{request.message}</p>}
                  <details className="customer-request-history">
                    <summary>{text('requestHistory')}</summary>
                    <ol>
                      {request.events.map((event, index) => (
                        <li key={`${event.event_type}-${event.created_at}-${index}`}>
                          <strong>{text(eventMessage(event.event_type))}</strong>
                          <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString(locale === 'am' ? 'am-ET' : 'en-ET')}</time>
                          {event.proposed_date && <span>{formatDate(event.proposed_date, locale)}{event.proposed_time ? ` · ${event.proposed_time.slice(0, 5)}` : ''}</span>}
                          {event.message && <p>{event.message}</p>}
                        </li>
                      ))}
                    </ol>
                  </details>
                  <div className="customer-request-actions">
                    {request.status === 'proposed' && (
                      <>
                        <button className="button button-primary button-small" type="button" disabled={busyRequest === request.id} onClick={() => void runAction(request, 'accept')}>
                          {text('acceptProposal')}
                        </button>
                        <button className="button button-outline button-small" type="button" disabled={busyRequest === request.id} onClick={() => void runAction(request, 'decline')}>
                          {text('declineProposal')}
                        </button>
                      </>
                    )}
                    {['pending', 'proposed', 'confirmed', 'declined'].includes(request.status) && (
                      <button className="button button-outline button-small" type="button" disabled={busyRequest === request.id} onClick={() => void runAction(request, 'cancel')}>
                        {text('cancelViewingRequest')}
                      </button>
                    )}
                    {request.status === 'cancelled' && (
                      <button className="button button-outline button-small" type="button" disabled={busyRequest === request.id} onClick={() => void deleteCancelledRequest(request)}>
                        <Trash2 size={14} aria-hidden="true" />{text('deleteCancelledRequest')}
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : !error ? (
            <div className="activity-empty">
              <CalendarClock size={25} aria-hidden="true" />
              <p>{text('noViewingActivity')}</p>
              <Link to="/">{text('browseAll')}</Link>
            </div>
          ) : null}

          <div className="manager-pagination customer-request-pagination">
            <span>{text('yourViewingRequestsCount').replace('{count}', String(count))}</span>
            <div>
              <button className="button button-outline button-small" type="button" disabled={!hasPrevious || loading} onClick={() => setPage((value) => value - 1)}>
                <ArrowLeft size={15} aria-hidden="true" />{text('previousPage')}
              </button>
              <span>{text('pageOf')} {page} / {Math.max(1, Math.ceil(count / 12))}</span>
              <button className="button button-outline button-small" type="button" disabled={!hasNext || loading} onClick={() => setPage((value) => value + 1)}>
                {text('nextPage')}<ArrowRight size={15} aria-hidden="true" />
              </button>
            </div>
          </div>
          <Link className="customer-inline-link" to="/account">{text('backToAccount')}</Link>
        </section>
      </section>
    </main>
  );
}
