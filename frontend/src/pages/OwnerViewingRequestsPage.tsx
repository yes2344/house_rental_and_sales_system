import { useEffect, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, CalendarClock, RotateCw } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import {
  getManagedViewingRequest,
  getManagedViewingRequests,
  updateManagedViewingRequest,
  type ManagedViewingRequest,
  type ManagedViewingRequestFilters,
  type ManagedViewingRequestPayload,
  type ViewingRequestStatus,
} from '../api/management';
import type { MessageKey } from '../i18n';

interface OwnerViewingRequestsPageProps {
  text: (key: MessageKey) => string;
}

const PAGE_SIZE = 12;

interface RequestFormValues {
  status: ViewingRequestStatus;
  scheduled_date: string;
  scheduled_time: string;
  agent_notes: string;
}

function formFromRequest(request: ManagedViewingRequest): RequestFormValues {
  return {
    status: request.status,
    scheduled_date: request.scheduled_date ?? '',
    scheduled_time: request.scheduled_time?.slice(0, 5) ?? '',
    agent_notes: request.agent_notes,
  };
}

function requestStatusMessage(status: ViewingRequestStatus): MessageKey {
  if (status === 'confirmed') return 'viewingConfirmed';
  if (status === 'rejected') return 'viewingRejected';
  return 'viewingPending';
}

export function OwnerViewingRequestsPage({ text }: OwnerViewingRequestsPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [requests, setRequests] = useState<ManagedViewingRequest[]>([]);
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [previousPage, setPreviousPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [selected, setSelected] = useState<ManagedViewingRequest | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [values, setValues] = useState<RequestFormValues | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState('');

  const rawPage = Number(searchParams.get('page') ?? 1);
  const page = Number.isInteger(rawPage) && rawPage > 1 ? rawPage : 1;
  const rawStatus = searchParams.get('status');
  const statusFilter = rawStatus === 'pending' || rawStatus === 'confirmed' || rawStatus === 'rejected'
    ? rawStatus
    : undefined;
  const rawOrdering = searchParams.get('ordering');
  const ordering = rawOrdering === 'preferred_date' || rawOrdering === 'scheduled_date'
    ? rawOrdering
    : '-created_at';

  useEffect(() => {
    const controller = new AbortController();
    const filters: ManagedViewingRequestFilters = {
      page_size: PAGE_SIZE,
      status: statusFilter,
      ordering,
      page,
    };
    setLoading(true);
    setLoadError('');
    void getManagedViewingRequests(filters, controller.signal)
      .then((response) => {
        setRequests(response.results);
        setCount(response.count);
        setNextPage(response.next);
        setPreviousPage(response.previous);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setRequests([]);
        setLoadError(getErrorMessage(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [ordering, page, reloadKey, statusFilter]);

  const chooseRequest = async (id: number) => {
    setDetailLoading(true);
    setDetailError('');
    setSaveError('');
    setSaveSuccess('');
    try {
      const request = await getManagedViewingRequest(id);
      setSelected(request);
      setValues(formFromRequest(request));
    } catch (error: unknown) {
      setSelected(null);
      setValues(null);
      setDetailError(getErrorMessage(error));
    } finally {
      setDetailLoading(false);
    }
  };

  const updateFormValue = <K extends keyof RequestFormValues>(name: K, value: RequestFormValues[K]) => {
    setValues((current) => current ? { ...current, [name]: value } : current);
    setSaveError('');
    setSaveSuccess('');
  };

  const saveRequest = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected || !values) return;
    setSaving(true);
    setSaveError('');
    setSaveSuccess('');
    const payload: ManagedViewingRequestPayload = {
      status: values.status,
      scheduled_date: values.scheduled_date || null,
      scheduled_time: values.scheduled_time || null,
      agent_notes: values.agent_notes,
    };
    try {
      const updated = await updateManagedViewingRequest(selected.id, payload);
      setSelected(updated);
      setValues(formFromRequest(updated));
      setRequests((current) => current.map((item) => item.id === updated.id ? updated : item));
      setSaveSuccess(text('requestManagementSaved'));
      setReloadKey((current) => current + 1);
    } catch (error: unknown) {
      setSaveError(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const updateFilter = (name: 'status' | 'ordering', value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(name, value);
    else next.delete(name);
    next.delete('page');
    setSearchParams(next);
  };

  const changePage = (nextPageValue: number) => {
    const next = new URLSearchParams(searchParams);
    if (nextPageValue > 1) next.set('page', String(nextPageValue));
    else next.delete('page');
    setSearchParams(next);
  };

  const preferredDate = (request: ManagedViewingRequest) =>
    `${request.preferred_date}${request.preferred_time ? ` · ${request.preferred_time.slice(0, 5)}` : ''}`;

  return (
    <main className="manager-page" id="main-content">
      <section className="manager-heading">
        <div>
          <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text('managerEyebrow')}</p>
          <h1>{text('managerViewingRequests')}</h1>
          <p>{text('managerViewingIntro')}</p>
        </div>
      </section>

      <div className="manager-filter-bar">
        <label className="manager-filter">
          <span>{text('requestStatus')}</span>
          <select value={statusFilter ?? ''} onChange={(event) => updateFilter('status', event.target.value)}>
            <option value="">{text('allStatuses')}</option>
            <option value="pending">{text('viewingPending')}</option>
            <option value="confirmed">{text('viewingConfirmed')}</option>
            <option value="rejected">{text('viewingRejected')}</option>
          </select>
        </label>
        <label className="manager-filter">
          <span>{text('sortBy')}</span>
          <select value={ordering} onChange={(event) => updateFilter('ordering', event.target.value)}>
            <option value="-created_at">{text('sortNewest')}</option>
            <option value="preferred_date">{text('sortPreferredDate')}</option>
            <option value="scheduled_date">{text('sortScheduledDate')}</option>
          </select>
        </label>
        <button className="button button-outline" type="button" onClick={() => setReloadKey((current) => current + 1)}>
          <RotateCw size={15} aria-hidden="true" />{text('refresh')}
        </button>
      </div>

      {loadError && <div className="manager-form-error" role="alert">{text('managerLoadError')} {loadError}</div>}
      {loading ? (
        <div className="listing-state" role="status"><span className="loading-spinner" />{text('managerLoadingRequests')}</div>
      ) : requests.length ? (
        <>
          <div className="manager-table-wrap">
            <table className="manager-table">
              <thead>
                <tr>
                  <th scope="col">{text('requester')}</th>
                  <th scope="col">{text('listingTitle')}</th>
                  <th scope="col">{text('preferredDate')}</th>
                  <th scope="col">{text('requestStatus')}</th>
                  <th scope="col"><span className="visually-hidden">{text('actions')}</span></th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr key={request.id} className={selected?.id === request.id ? 'is-selected' : ''}>
                    <td>
                      <strong>{request.full_name}</strong>
                      <span className="manager-row-secondary">{request.phone}</span>
                    </td>
                    <td>
                      <Link className="manager-row-property" to={`/owner/listings/${request.property.id}/edit`}>{request.property.title}</Link>
                      <span className="manager-row-secondary">{request.property.location}</span>
                    </td>
                    <td>{preferredDate(request)}</td>
                    <td><span className={`manager-badge request-${request.status}`}>{text(requestStatusMessage(request.status))}</span></td>
                    <td>
                      <button className="manager-row-action" type="button" onClick={() => void chooseRequest(request.id)}>
                        {text('reviewRequest')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="manager-pagination">
            <span>{text('managerResultCount').replace('{count}', String(count))}</span>
            <div>
              <button className="button button-outline button-small" type="button" disabled={!previousPage} onClick={() => changePage(page - 1)}>
                <ArrowLeft size={15} aria-hidden="true" />{text('previousPage')}
              </button>
              <span>{text('pageOf')} {page} / {Math.max(1, Math.ceil(count / PAGE_SIZE))}</span>
              <button className="button button-outline button-small" type="button" disabled={!nextPage} onClick={() => changePage(page + 1)}>
                {text('nextPage')}<ArrowRight size={15} aria-hidden="true" />
              </button>
            </div>
          </div>
        </>
      ) : !loadError ? (
        <div className="manager-state">
          <CalendarClock size={25} aria-hidden="true" />
          <h2>{text('noManagedRequests')}</h2>
          <p>{text('noManagedRequestsBody')}</p>
        </div>
      ) : null}

      {detailLoading && <div className="listing-state" role="status"><span className="loading-spinner" />{text('loadingRequestDetails')}</div>}
      {detailError && <div className="manager-form-error" role="alert">{detailError}</div>}
      {selected && values && (
        <section className="request-review-card" aria-labelledby="request-review-title">
          <div className="request-review-heading">
            <div>
              <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text('privateRequestDetails')}</p>
              <h2 id="request-review-title">{selected.full_name}</h2>
              <Link to={`/owner/listings/${selected.property.id}/edit`}>{selected.property.title}</Link>
            </div>
            <span className={`manager-badge request-${selected.status}`}>{text(requestStatusMessage(selected.status))}</span>
          </div>
          <div className="request-contact-grid">
            <div><span>{text('emailAddress')}</span><a href={`mailto:${selected.email}`}>{selected.email}</a></div>
            <div><span>{text('phoneNumber')}</span><a href={`tel:${selected.phone}`}>{selected.phone}</a></div>
            <div><span>{text('preferredDate')}</span><strong>{preferredDate(selected)}</strong></div>
            {selected.message && <div className="request-message"><span>{text('requestMessage')}</span><p>{selected.message}</p></div>}
          </div>
          <form className="request-update-form" onSubmit={(event) => void saveRequest(event)}>
            <h3>{text('manageRequest')}</h3>
            <div className="manager-form-grid">
              <label className="manager-field">
                <span>{text('requestStatus')}</span>
                <select value={values.status} onChange={(event) => updateFormValue('status', event.target.value as ViewingRequestStatus)}>
                  <option value="pending">{text('viewingPending')}</option>
                  <option value="confirmed">{text('viewingConfirmed')}</option>
                  <option value="rejected">{text('viewingRejected')}</option>
                </select>
              </label>
              <label className="manager-field">
                <span>{text('scheduledDate')}</span>
                <input type="date" value={values.scheduled_date} onChange={(event) => updateFormValue('scheduled_date', event.target.value)} />
              </label>
              <label className="manager-field">
                <span>{text('scheduledTime')}</span>
                <input type="time" value={values.scheduled_time} onChange={(event) => updateFormValue('scheduled_time', event.target.value)} />
              </label>
              <label className="manager-field manager-field-wide">
                <span>{text('privateAgentNotes')}</span>
                <textarea rows={4} value={values.agent_notes} onChange={(event) => updateFormValue('agent_notes', event.target.value)} />
              </label>
            </div>
            {saveError && <p className="manager-inline-error" role="alert">{saveError}</p>}
            {saveSuccess && <p className="manager-inline-success" role="status">{saveSuccess}</p>}
            <div className="manager-form-actions">
              <button className="button button-primary" type="submit" disabled={saving}>{saving ? text('savingRequest') : text('saveRequest')}</button>
              <button className="button button-outline" type="button" onClick={() => { setSelected(null); setValues(null); }}>
                <ArrowLeft size={15} aria-hidden="true" />{text('closeRequestDetails')}
              </button>
            </div>
          </form>
        </section>
      )}
    </main>
  );
}
