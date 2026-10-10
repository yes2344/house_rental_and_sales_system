import { Suspense, lazy, useEffect, useState, type FormEvent } from 'react';
import { CheckCircle2, MapPin, Plus, RotateCcw, Send, XCircle } from 'lucide-react';

import { getErrorMessage } from '../api/client';
import {
  getLocations,
  getMarketplaceNotifications,
  getOwnerAnnouncements,
  deleteOwnerAnnouncementImage,
  markMarketplaceNotificationRead,
  requestAnnouncementRenewal,
  submitOwnerAnnouncement,
  updateOwnerAnnouncement,
  withdrawOwnerAnnouncement,
  type MarketplaceLocation,
  type MarketplaceNotification,
  type OwnerAnnouncement,
  type OwnerAnnouncementPayload,
} from '../api/ownerAnnouncements';
import { hasPublicCoordinates } from '../components/propertyLocation';

const LocationMap = lazy(() =>
  import('../components/LocationMap').then((module) => ({ default: module.LocationMap })),
);

const statusLabels: Record<string, string> = {
  pending_review: 'Awaiting broker review',
  corrections_requested: 'Changes requested',
  approved: 'Approved',
  rejected: 'Not approved',
  suspended: 'Suspended',
  expired: 'Expired',
  withdrawn: 'Withdrawn',
};

const initialForm = {
  title: '',
  location: '',
  property_type: 'house',
  listing_type: 'sale' as 'sale' | 'rent',
  price: '',
  rental_frequency: '',
  bedrooms: 0,
  bathrooms: 0,
  area_sqft: 0,
  description: '',
  features: '',
  latitude: '',
  longitude: '',
  owner_contact_name: '',
  owner_contact_phone: '',
  owner_contact_email: '',
  authorization_confirmed: false,
  terms_accepted: false,
};

export function OwnerAnnouncementsPage() {
  const [announcements, setAnnouncements] = useState<OwnerAnnouncement[]>([]);
  const [editing, setEditing] = useState<OwnerAnnouncement | null>(null);
  const [notifications, setNotifications] = useState<MarketplaceNotification[]>([]);
  const [locations, setLocations] = useState<MarketplaceLocation[][]>([]);
  const [selectedLocationIds, setSelectedLocationIds] = useState<number[]>([]);
  const [values, setValues] = useState(initialForm);
  const [images, setImages] = useState<File[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [locationError, setLocationError] = useState('');

  const refresh = async () => {
    setLoading(true);
    try {
      const [response, notificationResponse] = await Promise.allSettled([
        getOwnerAnnouncements(),
        getMarketplaceNotifications(),
      ]);
      if (response.status === 'rejected') throw response.reason;
      setAnnouncements(response.value.results);
      setEditing((current) => current
        ? response.value.results.find((announcement) => announcement.id === current.id) ?? current
        : null);
      if (notificationResponse.status === 'fulfilled') {
        setNotifications(notificationResponse.value.results);
        setError('');
      } else {
        setError(getErrorMessage(notificationResponse.reason));
      }
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    const controller = new AbortController();
    void getLocations(undefined, controller.signal)
      .then((rootLocations) => setLocations([rootLocations]))
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) setError(getErrorMessage(requestError));
      });
    return () => controller.abort();
  }, []);

  const setField = <K extends keyof typeof initialForm>(field: K, value: (typeof initialForm)[K]) => {
    setValues((current) => ({ ...current, [field]: value }));
  };

  const chooseLocation = async (level: number, rawId: string) => {
    const nextIds = selectedLocationIds.slice(0, level);
    if (rawId) nextIds.push(Number(rawId));
    setSelectedLocationIds(nextIds);
    setLocations((current) => current.slice(0, level + 1));
    if (rawId) {
      try {
        const children = await getLocations(Number(rawId));
        if (children.length) {
          setLocations((current) => [...current.slice(0, level + 1), children]);
        }
      } catch (requestError: unknown) {
        setError(getErrorMessage(requestError));
      }
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    setNotice('');
    const payload: OwnerAnnouncementPayload = {
      ...values,
      administrative_location: selectedLocationIds.at(-1) ?? editing?.property.administrative_location ?? null,
      latitude: values.latitude || null,
      longitude: values.longitude || null,
      images,
    };
    if (Boolean(values.latitude) !== Boolean(values.longitude)) {
      setError('Enter both coordinates, or clear both fields.');
      setSubmitting(false);
      return;
    }
    try {
      if (editing) await updateOwnerAnnouncement(editing.id, payload);
      else await submitOwnerAnnouncement(payload);
      setEditing(null);
      setValues(initialForm);
      setImages([]);
      setSelectedLocationIds([]);
      setNotice(editing
        ? 'Your changes were submitted for broker review.'
        : 'Your announcement was submitted. A broker will review it and notify you of the decision.');
      await refresh();
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const performAction = async (announcement: OwnerAnnouncement, action: 'withdraw' | 'renew') => {
    setError('');
    try {
      if (action === 'withdraw') await withdrawOwnerAnnouncement(announcement.id);
      else await requestAnnouncementRenewal(announcement.id);
      setNotice(action === 'withdraw' ? 'Announcement withdrawn.' : 'Renewal request sent to the brokerage.');
      await refresh();
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
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

  const editAnnouncement = (announcement: OwnerAnnouncement) => {
    setEditing(announcement);
    setSelectedLocationIds([]);
    setValues({
      title: announcement.property.title,
      location: announcement.property.location,
      property_type: announcement.property.property_type,
      listing_type: announcement.property.listing_type,
      price: announcement.property.price,
      rental_frequency: announcement.property.rental_frequency,
      bedrooms: announcement.property.bedrooms,
      bathrooms: announcement.property.bathrooms,
      area_sqft: announcement.property.area_sqft,
      description: announcement.property.description,
      features: announcement.property.features,
      latitude: announcement.property.latitude === null ? '' : String(announcement.property.latitude),
      longitude: announcement.property.longitude === null ? '' : String(announcement.property.longitude),
      owner_contact_name: announcement.owner_contact_name,
      owner_contact_phone: announcement.owner_contact_phone,
      owner_contact_email: announcement.owner_contact_email,
      authorization_confirmed: true,
      terms_accepted: true,
    });
    setImages([]);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const removeImage = async (announcement: OwnerAnnouncement, imageId: number) => {
    try {
      await deleteOwnerAnnouncementImage(announcement.id, imageId);
      await refresh();
      setNotice('Property photo removed. Changes to an approved listing require broker review.');
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    }
  };

  const useCurrentLocation = () => {
    setLocationError('');
    if (!navigator.geolocation) {
      setLocationError('This browser does not provide location access. You can still select a point on the map or enter coordinates.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setField('latitude', position.coords.latitude.toFixed(6));
        setField('longitude', position.coords.longitude.toFixed(6));
      },
      () => setLocationError('Current location could not be accessed. You can still select a point on the map or enter coordinates.'),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const selectedCoordinates = hasPublicCoordinates(values.latitude, values.longitude)
    ? { latitude: Number(values.latitude), longitude: Number(values.longitude) }
    : null;

  return (
    <main className="account-page" id="main-content">
      <div className="container account-content">
        <header className="section-heading">
          <div>
            <p className="eyebrow eyebrow-muted">Owner service</p>
            <h1>Announce your property</h1>
            <p className="section-description">
              Send property details to the brokerage for review. Your listing is not public until an agreement is approved.
            </p>
          </div>
        </header>
        {error && <p className="auth-form-error" role="alert">{error}</p>}
        {notice && <p className="form-success" role="status"><CheckCircle2 size={17} />{notice}</p>}

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

        <section className="auth-card owner-announcement-form">
          <h2><Plus size={19} aria-hidden="true" /> {editing ? `Edit ${editing.property.title}` : 'Property details'}</h2>
          {editing && <button type="button" className="filter-clear" onClick={() => { setEditing(null); setValues(initialForm); setImages([]); }}>Cancel editing</button>}
          <form className="auth-form" onSubmit={submit}>
            <label>Property title *
              <input required maxLength={200} value={values.title} onChange={(event) => setField('title', event.target.value)} />
            </label>
            <label>Address or area *
              <input required maxLength={200} value={values.location} onChange={(event) => setField('location', event.target.value)} />
            </label>
            <fieldset>
              <legend>Administrative location (optional)</legend>
              <div className="search-fields">
                {locations.map((options, level) => (
                  <label className="search-field" key={level}>
                    <span>{level === 0 ? 'Country / root' : 'Child location'}</span>
                    <select
                      value={selectedLocationIds[level] ?? ''}
                      onChange={(event) => void chooseLocation(level, event.target.value)}
                    >
                      <option value="">Select a location</option>
                      {options.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="search-fields">
              <label className="search-field">Property type
                <select value={values.property_type} onChange={(event) => setField('property_type', event.target.value)}>
                  {['house', 'villa', 'apartment', 'condominium', 'land', 'office', 'shop', 'warehouse', 'commercial', 'other']
                    .map((type) => <option key={type} value={type}>{type}</option>)}
                </select>
              </label>
              <label className="search-field">Listing type
                <select
                  value={values.listing_type}
                  onChange={(event) => {
                    const listingType = event.target.value as 'sale' | 'rent';
                    setField('listing_type', listingType);
                    setField('rental_frequency', listingType === 'rent' ? values.rental_frequency || 'monthly' : '');
                  }}
                >
                  <option value="sale">For sale</option><option value="rent">For rent</option>
                </select>
              </label>
              <label className="search-field">Price (ETB) *
                <input type="number" min="0.01" step="0.01" required value={values.price} onChange={(event) => setField('price', event.target.value)} />
              </label>
              {values.listing_type === 'rent' && (
                <label className="search-field">Rent frequency
                  <select value={values.rental_frequency} onChange={(event) => setField('rental_frequency', event.target.value)}>
                    <option value="daily">Daily</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option>
                  </select>
                </label>
              )}
              {(['bedrooms', 'bathrooms', 'area_sqft'] as const).map((field) => (
                <label className="search-field" key={field}>{field.replace('_', ' ')}
                  <input type="number" min="0" value={values[field]} onChange={(event) => setField(field, Number(event.target.value))} />
                </label>
              ))}
            </div>
            <label>Description *
              <textarea required maxLength={10000} rows={5} value={values.description} onChange={(event) => setField('description', event.target.value)} />
            </label>
            <label>Features
              <textarea maxLength={5000} rows={3} value={values.features} onChange={(event) => setField('features', event.target.value)} />
            </label>
            <fieldset>
              <legend>Optional precise location</legend>
              <p className="auth-field-hint">Exact coordinates stay private unless the broker explicitly approves public map display.</p>
              <p className="auth-field-hint">Use GPS only if you are at the property; otherwise select its actual position on the map or enter coordinates manually.</p>
              <button className="button button-outline" type="button" onClick={useCurrentLocation}>Use my current location</button>
              {locationError && <p className="filter-validation" role="status">{locationError}</p>}
              <div className="filter-two-columns">
                <label className="filter-label">Latitude
                  <input className="filter-input" type="number" min="-90" max="90" step="0.000001" value={values.latitude} onChange={(event) => setField('latitude', event.target.value)} />
                </label>
                <label className="filter-label">Longitude
                  <input className="filter-input" type="number" min="-180" max="180" step="0.000001" value={values.longitude} onChange={(event) => setField('longitude', event.target.value)} />
                </label>
              </div>
              <button className="filter-clear" type="button" onClick={() => { setField('latitude', ''); setField('longitude', ''); }}>
                Clear coordinates
              </button>
              <Suspense fallback={<p role="status">Loading map…</p>}>
                <LocationMap
                  coordinates={selectedCoordinates}
                  interactive
                  markerLabel={values.location || values.title || 'Property location'}
                  onCoordinatesChange={(coordinates) => {
                    setField('latitude', coordinates.latitude.toFixed(6));
                    setField('longitude', coordinates.longitude.toFixed(6));
                  }}
                />
              </Suspense>
            </fieldset>
            <label>Property photos (up to 10)
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={(event) => {
                  const selected = Array.from(event.target.files ?? []);
                  const availableSlots = 10 - (editing?.property.images.length ?? 0);
                  if (selected.length > availableSlots) {
                    setError(`You can add at most ${Math.max(availableSlots, 0)} more photo(s).`);
                  } else {
                    setError('');
                    setImages(selected);
                  }
                }}
              />
            </label>
            {editing?.property.images.length ? (
              <div className="owner-announcement-images">
                {editing.property.images.map((image) => image.url && (
                  <div key={image.id}>
                    <img src={image.url} alt={image.caption || editing.property.title} loading="lazy" />
                    <button type="button" className="filter-clear" onClick={() => void removeImage(editing, image.id)}>Remove photo</button>
                  </div>
                ))}
              </div>
            ) : null}
            <p className="auth-field-hint">A phone number or email is collected for brokerage contact. This project does not yet verify contact ownership.</p>
            <label>Owner / authorized contact name *
              <input required maxLength={200} value={values.owner_contact_name} onChange={(event) => setField('owner_contact_name', event.target.value)} />
            </label>
            <label>Contact phone *
              <input required type="tel" maxLength={50} value={values.owner_contact_phone} onChange={(event) => setField('owner_contact_phone', event.target.value)} />
            </label>
            <label>Contact email
              <input type="email" maxLength={254} value={values.owner_contact_email} onChange={(event) => setField('owner_contact_email', event.target.value)} />
            </label>
            <label className="checkbox-field">
              <input type="checkbox" checked={values.authorization_confirmed} onChange={(event) => setField('authorization_confirmed', event.target.checked)} required />
              I am the owner or have authorization to advertise this property.
            </label>
            <label className="checkbox-field">
              <input type="checkbox" checked={values.terms_accepted} onChange={(event) => setField('terms_accepted', event.target.checked)} required />
              I accept the brokerage review and agreement process.
            </label>
            <button className="button button-primary" type="submit" disabled={submitting}>
              <Send size={16} aria-hidden="true" />{submitting ? 'Submitting…' : editing ? 'Save changes for review' : 'Submit for broker review'}
            </button>
          </form>
        </section>

        <section className="section">
          <h2>Your announcements</h2>
          {loading ? <p role="status">Loading announcements…</p> : announcements.length === 0 ? (
            <p>No property announcements yet.</p>
          ) : (
            <div className="owner-announcement-list">
              {announcements.map((announcement) => (
                <article className="auth-card owner-announcement-card" key={announcement.id}>
                  <div>
                    <h3>{announcement.property.title}</h3>
                    <p><MapPin size={14} aria-hidden="true" /> {announcement.property.location}</p>
                    <strong>{statusLabels[announcement.status] ?? announcement.status}</strong>
                    {announcement.broker_feedback && <p>{announcement.broker_feedback}</p>}
                    <div className="owner-announcement-images">
                      {announcement.property.images.map((image) => image.url && (
                        <img key={image.id} src={image.url} alt={image.caption || announcement.property.title} loading="lazy" />
                      ))}
                    </div>
                    {announcement.agreements[0] && (
                      <>
                        <p>Agreement: {announcement.agreements[0].start_date} – {announcement.agreements[0].end_date}</p>
                        <p>Terms: {announcement.agreements[0].terms}</p>
                        {announcement.agreements[0].renewal_conditions && (
                          <p>Renewal conditions: {announcement.agreements[0].renewal_conditions}</p>
                        )}
                      </>
                    )}
                  </div>
                  {!['suspended', 'expired', 'withdrawn'].includes(announcement.status) && (
                    <button className="button button-outline" type="button" onClick={() => editAnnouncement(announcement)}>
                      Edit details
                    </button>
                  )}
                  {['approved', 'expired'].includes(announcement.status) && (
                    <button className="button button-outline" type="button" onClick={() => void performAction(announcement, 'renew')}>
                      <RotateCcw size={15} aria-hidden="true" /> Request renewal
                    </button>
                  )}
                  {!['withdrawn', 'expired', 'suspended'].includes(announcement.status) && (
                    <button className="button button-outline" type="button" onClick={() => void performAction(announcement, 'withdraw')}>
                      <XCircle size={15} aria-hidden="true" /> Withdraw
                    </button>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
