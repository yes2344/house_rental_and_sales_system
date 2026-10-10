import { lazy, Suspense, useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { ArrowLeft, ImagePlus, LocateFixed, Star, Trash2, Upload } from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import { getApiFieldErrors, getErrorMessage } from '../api/client';
import type { PropertyCoordinates } from '../components/LocationMap';
import {
  createManagedProperty,
  deleteManagedImage,
  deleteManagedProperty,
  getAmenities,
  getManagedImages,
  getManagedProperty,
  updateManagedImage,
  updateManagedProperty,
  uploadManagedImage,
  type AmenityOption,
  type ManagedImage,
  type ManagedListingType,
  type ManagedProperty,
  type ManagedPropertyPayload,
  type ManagedAreaUnit,
  type ManagedRentalFrequency,
  type ManagedPropertyStatus,
  type ManagedPropertyType,
} from '../api/management';
import type { Locale, MessageKey } from '../i18n';

const LocationMap = lazy(() =>
  import('../components/LocationMap').then((module) => ({ default: module.LocationMap })),
);

interface OwnerPropertyFormPageProps {
  locale: Locale;
  text: (key: MessageKey) => string;
}

interface PropertyFormValues {
  title: string;
  location: string;
  latitude: string;
  longitude: string;
  exact_location_is_public: boolean;
  category: ManagedPropertyType;
  listing_type: ManagedListingType;
  price: string;
  bedrooms: string;
  bathrooms: string;
  area_sqft: string;
  area_value: string;
  area_unit: ManagedAreaUnit;
  rental_frequency: ManagedRentalFrequency;
  description: string;
  features: string;
  status: ManagedPropertyStatus;
  amenities: number[];
  contact_name: string;
  contact_phone: string;
  contact_email: string;
}

const initialValues: PropertyFormValues = {
  title: '',
  location: '',
  latitude: '',
  longitude: '',
  exact_location_is_public: false,
  category: 'house',
  listing_type: 'sale',
  price: '',
  bedrooms: '',
  bathrooms: '',
  area_sqft: '',
  area_value: '',
  area_unit: '',
  rental_frequency: '',
  description: '',
  features: '',
  status: 'available',
  amenities: [],
  contact_name: '',
  contact_phone: '',
  contact_email: '',
};

function fromProperty(property: ManagedProperty): PropertyFormValues {
  return {
    title: property.title,
    location: property.location,
    latitude: property.latitude === null ? '' : String(property.latitude),
    longitude: property.longitude === null ? '' : String(property.longitude),
    exact_location_is_public: property.exact_location_is_public,
    category: property.category,
    listing_type: property.listing_type,
    price: property.price,
    bedrooms: String(property.bedrooms),
    bathrooms: String(property.bathrooms),
    area_sqft: String(property.area_sqft),
    area_value: property.area_value ?? (property.area_sqft ? String(property.area_sqft) : ''),
    area_unit: property.area_unit || (property.area_sqft ? 'sqft' : ''),
    rental_frequency: property.rental_frequency,
    description: property.description,
    features: property.features,
    status: property.status,
    amenities: property.amenities,
    contact_name: property.contact_name,
    contact_phone: property.contact_phone,
    contact_email: property.contact_email,
  };
}

function isCreatedNavigationState(state: unknown): state is { created: true; available: boolean } {
  return typeof state === 'object' && state !== null && 'created' in state
    && state.created === true && 'available' in state && typeof state.available === 'boolean';
}

function statusText(status: ManagedPropertyStatus, text: (key: MessageKey) => string): string {
  if (status === 'rented') return text('statusRented');
  if (status === 'sold') return text('statusSold');
  if (status === 'inactive') return text('statusInactive');
  return text('available');
}

const publicationMessage: Record<ManagedProperty['publication_status'], MessageKey> = {
  draft: 'publicationDraft',
  pending_review: 'publicationPending',
  published: 'publicationPublished',
  rejected: 'publicationRejected',
  suspended: 'publicationSuspended',
};

export function OwnerPropertyFormPage({ locale, text }: OwnerPropertyFormPageProps) {
  const { id: idParam } = useParams();
  const propertyId = idParam ? Number(idParam) : null;
  const navigate = useNavigate();
  const location = useLocation();
  const isEditing = propertyId !== null && Number.isInteger(propertyId) && propertyId > 0;
  const invalidEditId = idParam !== undefined && !isEditing;
  const [values, setValues] = useState(initialValues);
  const [property, setProperty] = useState<ManagedProperty | null>(null);
  const [amenities, setAmenities] = useState<AmenityOption[]>([]);
  const [images, setImages] = useState<ManagedImage[]>([]);
  const [loading, setLoading] = useState(isEditing);
  const [amenityError, setAmenityError] = useState('');
  const [pageError, setPageError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState('');
  const [imageBusyId, setImageBusyId] = useState<number | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageCaption, setImageCaption] = useState('');
  const [makePrimary, setMakePrimary] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [gpsMessage, setGpsMessage] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(Boolean(isEditing));
    setPageError('');
    setAmenityError('');
    void getAmenities(controller.signal)
      .then(setAmenities)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setAmenityError(getErrorMessage(error));
      });

    if (isEditing && propertyId !== null) {
      void Promise.all([
        getManagedProperty(propertyId, controller.signal),
        getManagedImages(propertyId, controller.signal),
      ])
        .then(([managedProperty, managedImages]) => {
          setProperty(managedProperty);
          setValues(fromProperty(managedProperty));
          setImages(managedImages);
        })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) setPageError(getErrorMessage(error));
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    } else {
      setProperty(null);
      setValues(initialValues);
      setImages([]);
      setLoading(false);
    }
    return () => controller.abort();
  }, [isEditing, propertyId]);

  const updateValue = <K extends keyof PropertyFormValues>(name: K, value: PropertyFormValues[K]) => {
    setValues((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: '' }));
    setSaveError('');
    setSaveSuccess('');
  };

  const onListingTypeChange = (value: ManagedListingType) => {
    setValues((current) => ({
      ...current,
      listing_type: value,
      status: current.status === 'sold' || current.status === 'rented' ? 'available' : current.status,
      rental_frequency: value === 'sale' ? '' : current.rental_frequency,
    }));
    setFieldErrors((current) => ({ ...current, listing_type: '', status: '', rental_frequency: '' }));
  };

  const onAmenityToggle = (amenityId: number) => {
    const selected = values.amenities.includes(amenityId);
    updateValue(
      'amenities',
      selected
        ? values.amenities.filter((id) => id !== amenityId)
        : [...values.amenities, amenityId],
    );
  };

  const updateCoordinates = (coordinates: PropertyCoordinates) => {
    updateValue('latitude', coordinates.latitude.toFixed(6));
    updateValue('longitude', coordinates.longitude.toFixed(6));
  };

  const useCurrentLocation = () => {
    setGpsMessage('');
    if (!navigator.geolocation) {
      setGpsMessage(text('gpsUnavailable'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        updateCoordinates({
          latitude: coords.latitude,
          longitude: coords.longitude,
        });
        setGpsMessage(text('gpsLocationLoaded'));
      },
      (error) => {
        setGpsMessage(
          error.code === error.PERMISSION_DENIED
            ? text('gpsPermissionDenied')
            : text('gpsUnavailable'),
        );
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    );
  };

  const submitProperty = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setSaveError('');
    setSaveSuccess('');
    setFieldErrors({});
    const payload: ManagedPropertyPayload = {
      ...values,
      latitude: values.latitude.trim() || null,
      longitude: values.longitude.trim() || null,
      price: values.price.trim(),
      bedrooms: values.bedrooms ? Number(values.bedrooms) : 0,
      bathrooms: values.bathrooms ? Number(values.bathrooms) : 0,
      area_sqft: values.area_unit === 'sqft' && values.area_value
        ? Math.round(Number(values.area_value))
        : 0,
      area_value: values.area_value ? values.area_value : null,
      area_unit: values.area_value ? values.area_unit : '',
      rental_frequency: values.listing_type === 'rent' ? values.rental_frequency : '',
    };
    try {
      if (isEditing && propertyId !== null) {
        const updated = await updateManagedProperty(propertyId, payload);
        setProperty(updated);
        setValues(fromProperty(updated));
        setSaveSuccess(text('listingSaved'));
      } else {
        const created = await createManagedProperty(payload);
        navigate(`/management/listings/${created.id}/edit`, {
          replace: true,
          state: { created: true, available: created.status === 'available' },
        });
      }
    } catch (error: unknown) {
      setFieldErrors(getApiFieldErrors(error));
      setSaveError(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const refreshImages = async () => {
    if (propertyId === null) return;
    setImageLoading(true);
    setImageError('');
    try {
      setImages(await getManagedImages(propertyId));
    } catch (error: unknown) {
      setImageError(getErrorMessage(error));
    } finally {
      setImageLoading(false);
    }
  };

  const chooseImage = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    setImageFile(nextFile);
    setImageError('');
    if (nextFile) {
      const extension = nextFile.name.split('.').pop()?.toLowerCase();
      if (!['jpg', 'jpeg', 'png', 'webp'].includes(extension ?? '')) {
        setImageError(text('imageTypeError'));
        setImageFile(null);
      } else if (nextFile.size > 10 * 1024 * 1024) {
        setImageError(text('imageSizeError'));
        setImageFile(null);
      }
    }
  };

  const submitImage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isEditing || propertyId === null || !imageFile) {
      setImageError(text('imageChooseFile'));
      return;
    }
    if (images.length >= 10) {
      setImageError(text('imageLimitError'));
      return;
    }
    setImageBusyId(-1);
    setImageError('');
    try {
      await uploadManagedImage(propertyId, imageFile, imageCaption.trim(), makePrimary);
      setImageFile(null);
      setImageCaption('');
      setMakePrimary(false);
      const input = document.getElementById('property-image-file');
      if (input instanceof HTMLInputElement) input.value = '';
      await refreshImages();
    } catch (error: unknown) {
      setImageError(getErrorMessage(error));
    } finally {
      setImageBusyId(null);
    }
  };

  const setPrimaryImage = async (imageId: number) => {
    if (propertyId === null) return;
    setImageBusyId(imageId);
    setImageError('');
    try {
      await updateManagedImage(propertyId, imageId, { is_primary: true });
      await refreshImages();
    } catch (error: unknown) {
      setImageError(getErrorMessage(error));
    } finally {
      setImageBusyId(null);
    }
  };

  const removeImage = async (image: ManagedImage) => {
    if (propertyId === null || !window.confirm(text('confirmDeleteImage'))) return;
    setImageBusyId(image.id);
    setImageError('');
    try {
      await deleteManagedImage(propertyId, image.id);
      await refreshImages();
    } catch (error: unknown) {
      setImageError(getErrorMessage(error));
    } finally {
      setImageBusyId(null);
    }
  };

  const removeProperty = async () => {
    if (propertyId === null || !window.confirm(text('confirmDeleteListing'))) return;
    setDeleting(true);
    setSaveError('');
    try {
      await deleteManagedProperty(propertyId);
      navigate('/management/listings', { replace: true });
    } catch (error: unknown) {
      setSaveError(getErrorMessage(error));
      setDeleting(false);
    }
  };

  const fieldError = (field: keyof PropertyFormValues) =>
    fieldErrors[field] ? <span className="field-error">{fieldErrors[field]}</span> : null;

  if (loading) {
    return <main className="manager-page" id="main-content"><div className="listing-state" role="status"><span className="loading-spinner" />{text('managerLoadingProperty')}</div></main>;
  }

  if (invalidEditId) {
    return (
      <main className="manager-page" id="main-content">
        <div className="manager-state manager-error" role="alert">
          <h1>{text('managerLoadError')}</h1>
          <p>{text('invalidListingId')}</p>
          <Link className="button button-outline" to="/management/listings">{text('backToListings')}</Link>
        </div>
      </main>
    );
  }

  if (pageError) {
    return (
      <main className="manager-page" id="main-content">
        <div className="manager-state manager-error" role="alert">
          <h1>{text('managerLoadError')}</h1><p>{pageError}</p>
          <Link className="button button-outline" to="/management/listings">{text('backToListings')}</Link>
        </div>
      </main>
    );
  }

  const allowedStatuses: ManagedPropertyStatus[] = values.listing_type === 'rent'
    ? ['available', 'rented', 'inactive']
    : ['available', 'sold', 'inactive'];
  const latitude = Number(values.latitude);
  const longitude = Number(values.longitude);
  const selectedCoordinates = values.latitude.trim() && values.longitude.trim()
    && Number.isFinite(latitude) && latitude >= -90 && latitude <= 90
    && Number.isFinite(longitude) && longitude >= -180 && longitude <= 180
    ? { latitude, longitude }
    : null;

  return (
    <main className="manager-page" id="main-content">
      <section className="manager-heading">
        <div>
          <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text('managerEyebrow')}</p>
          <h1>{text(isEditing ? 'editListing' : 'createListing')}</h1>
          <p>{text(isEditing ? 'editListingIntro' : 'createListingIntro')}</p>
        </div>
        <Link className="button button-outline" to="/management/listings"><ArrowLeft size={16} aria-hidden="true" />{text('backToListings')}</Link>
      </section>

      {isEditing && property && (
        <section className="publication-note" aria-label={text('publicationStatus')}>
          <strong>{text('publicationStatus')}: {text(publicationMessage[property.publication_status])}</strong>
          <p>{text('publicationReadOnlyNote')}</p>
          {property.publication_status === 'rejected' && property.moderation_note && (
            <p><strong>{text('moderationFeedback')}:</strong> {property.moderation_note}</p>
          )}
        </section>
      )}

      {isCreatedNavigationState(location.state) && (
        <div className="manager-success" role="status">
          {text(location.state.available ? 'listingCreated' : 'listingCreatedUnavailable')}
        </div>
      )}
      {saveSuccess && <div className="manager-success" role="status">{saveSuccess}</div>}
      {saveError && <div className="manager-form-error" role="alert">{saveError}</div>}

      <form className="manager-form" onSubmit={(event) => void submitProperty(event)}>
        <section className="manager-form-section">
          <h2>{text('listingInformation')}</h2>
          <div className="manager-form-grid">
            <label className="manager-field manager-field-wide">
              <span>{text('listingTitle')} *</span>
              <input required maxLength={200} value={values.title} onChange={(event) => updateValue('title', event.target.value)} />
              {fieldError('title')}
            </label>
            <label className="manager-field">
              <span>{text('location')} *</span>
              <input required maxLength={200} value={values.location} onChange={(event) => updateValue('location', event.target.value)} />
              {fieldError('location')}
            </label>
            <label className="manager-field">
              <span>{text('categoryLabel')} *</span>
              <select value={values.category} onChange={(event) => updateValue('category', event.target.value as ManagedPropertyType)}>
                <option value="house">{text('house')}</option>
                <option value="villa">{text('villa')}</option>
                <option value="villa">{text('house')}</option>
                <option value="apartment">{text('apartment')}</option>
                <option value="condominium">Condominium</option>
                <option value="land">{text('land')}</option>
                <option value="office">Office</option>
                <option value="shop">Shop</option>
                <option value="warehouse">Warehouse</option>
                <option value="commercial">{text('commercial')}</option>
                <option value="other">Other</option>
              </select>
              {fieldError('category')}
            </label>
            <label className="manager-field">
              <span>{text('listingTypeLabel')} *</span>
              <select value={values.listing_type} onChange={(event) => onListingTypeChange(event.target.value as ManagedListingType)}>
                <option value="sale">{text('forSale')}</option>
                <option value="rent">{text('forRent')}</option>
              </select>
              {fieldError('listing_type')}
            </label>
            <label className="manager-field">
              <span>{text('priceLabel')} (ETB) *</span>
              <input type="number" required min="0.01" step="0.01" value={values.price} onChange={(event) => updateValue('price', event.target.value)} />
              {fieldError('price')}
            </label>
            <label className="manager-field">
              <span>{text('listingStatus')} *</span>
              <select value={values.status} onChange={(event) => updateValue('status', event.target.value as ManagedPropertyStatus)}>
                {allowedStatuses.map((status) => <option key={status} value={status}>{statusText(status, text)}</option>)}
              </select>
              {fieldError('status')}
            </label>
            <label className="manager-field">
              <span>{text('bedrooms')}</span>
              <input type="number" min="0" step="1" value={values.bedrooms} onChange={(event) => updateValue('bedrooms', event.target.value)} />
              {fieldError('bedrooms')}
            </label>
            <label className="manager-field">
              <span>{text('bathrooms')}</span>
              <input type="number" min="0" step="1" value={values.bathrooms} onChange={(event) => updateValue('bathrooms', event.target.value)} />
              {fieldError('bathrooms')}
            </label>
            <label className="manager-field">
              <span>{text('sizeLabel')}</span>
              <input type="number" min="0.01" step="0.01" value={values.area_value} onChange={(event) => updateValue('area_value', event.target.value)} />
              {fieldError('area_value')}
            </label>
            <label className="manager-field">
              <span>{text('areaUnit')}</span>
              <select value={values.area_unit} onChange={(event) => updateValue('area_unit', event.target.value as ManagedAreaUnit)}>
                <option value="">{text('optionalField')}</option>
                <option value="sqm">{text('squareMetres')}</option>
                <option value="sqft">{text('squareFeet')}</option>
              </select>
              {fieldError('area_unit')}
            </label>
            {values.listing_type === 'rent' && (
              <label className="manager-field">
                <span>{text('rentalFrequency')} *</span>
                <select value={values.rental_frequency} onChange={(event) => updateValue('rental_frequency', event.target.value as ManagedRentalFrequency)}>
                  <option value="">{text('selectOption')}</option>
                  <option value="daily">{text('daily')}</option>
                  <option value="monthly">{text('monthly')}</option>
                  <option value="yearly">{text('yearly')}</option>
                </select>
                {fieldError('rental_frequency')}
              </label>
            )}
            <label className="manager-field manager-field-wide">
              <span>{text('detailsHeading')} *</span>
              <textarea required rows={5} value={values.description} onChange={(event) => updateValue('description', event.target.value)} />
              {fieldError('description')}
            </label>
            <label className="manager-field manager-field-wide">
              <span>{text('featuresLabel')}</span>
              <textarea rows={3} value={values.features} onChange={(event) => updateValue('features', event.target.value)} />
              {fieldError('features')}
            </label>
          </div>
        </section>

        <section className="manager-form-section">
          <h2>{text('propertyLocation')}</h2>
          <p className="manager-hint">{text('propertyLocationHint')}</p>
          <div className="location-picker-actions">
            <button className="button button-outline button-small" type="button" onClick={useCurrentLocation}>
              <LocateFixed size={15} aria-hidden="true" />{text('useCurrentLocation')}
            </button>
            <button
              className="button button-outline button-small"
              type="button"
              onClick={() => {
                updateValue('latitude', '');
                updateValue('longitude', '');
                setGpsMessage('');
              }}
              disabled={!values.latitude && !values.longitude}
            >
              {text('clearLocation')}
            </button>
          </div>
          {gpsMessage && <p className="location-gps-message" role="status">{gpsMessage}</p>}
          <Suspense fallback={<div className="property-map map-loading" role="status">{text('loadingMap')}</div>}>
            <LocationMap
              coordinates={selectedCoordinates}
              interactive
              onCoordinatesChange={updateCoordinates}
              markerLabel={text('selectedPropertyLocation')}
            />
          </Suspense>
          <p className="manager-hint location-map-hint">{text('mapSelectionHint')}</p>
          <div className="manager-form-grid">
            <label className="manager-field">
              <span>{text('latitude')}</span>
              <input
                type="number"
                step="0.000001"
                min="-90"
                max="90"
                value={values.latitude}
                onChange={(event) => updateValue('latitude', event.target.value)}
              />
              {fieldError('latitude')}
            </label>
            <label className="manager-field">
              <span>{text('longitude')}</span>
              <input
                type="number"
                step="0.000001"
                min="-180"
                max="180"
                value={values.longitude}
                onChange={(event) => updateValue('longitude', event.target.value)}
              />
              {fieldError('longitude')}
            </label>
          </div>
          <p className="location-coordinate-preview" aria-live="polite">
            {selectedCoordinates
              ? `${text('selectedCoordinates')}: ${selectedCoordinates.latitude.toFixed(6)}, ${selectedCoordinates.longitude.toFixed(6)}`
              : text('noLocationSelected')}
          </p>
          <label className="amenity-choice location-visibility-choice">
            <input
              type="checkbox"
              checked={values.exact_location_is_public}
              onChange={(event) => updateValue('exact_location_is_public', event.target.checked)}
            />
            <span>{text('showExactLocation')}</span>
          </label>
          <p className="manager-hint location-map-hint">{text('exactLocationPrivacyHint')}</p>
        </section>

        <section className="manager-form-section">
          <h2>{text('amenitiesHeading')}</h2>
          {amenityError ? (
            <p className="manager-inline-error" role="alert">{text('amenityLoadError')} {amenityError}</p>
          ) : amenities.length ? (
            <div className="amenity-choice-grid">
              {amenities.map((amenity) => (
                <label key={amenity.id} className="amenity-choice">
                  <input type="checkbox" checked={values.amenities.includes(amenity.id)} onChange={() => onAmenityToggle(amenity.id)} />
                  <span>{locale === 'am' && amenity.name_am ? amenity.name_am : amenity.name}</span>
                </label>
              ))}
            </div>
          ) : (
            <p className="manager-hint">{text('noAmenitiesAvailable')}</p>
          )}
        </section>

        <section className="manager-form-section">
          <h2>{text('listingContactDetails')}</h2>
          <p className="manager-hint">{text('listingContactHint')}</p>
          <div className="manager-form-grid">
            <label className="manager-field">
              <span>{text('contactPerson')}</span>
              <input maxLength={200} value={values.contact_name} onChange={(event) => updateValue('contact_name', event.target.value)} />
              {fieldError('contact_name')}
            </label>
            <label className="manager-field">
              <span>{text('contactByPhone')}</span>
              <input maxLength={50} value={values.contact_phone} onChange={(event) => updateValue('contact_phone', event.target.value)} />
              {fieldError('contact_phone')}
            </label>
            <label className="manager-field manager-field-wide">
              <span>{text('contactByEmail')}</span>
              <input type="email" value={values.contact_email} onChange={(event) => updateValue('contact_email', event.target.value)} />
              {fieldError('contact_email')}
            </label>
          </div>
        </section>

        <div className="manager-form-actions">
          <button className="button button-primary" type="submit" disabled={saving || deleting}>
            {saving ? text('savingListing') : text('saveListing')}
          </button>
          {isEditing && (
            <button className="button button-danger" type="button" disabled={deleting || saving} onClick={() => void removeProperty()}>
              <Trash2 size={15} aria-hidden="true" />{deleting ? text('deletingListing') : text('deleteListing')}
            </button>
          )}
        </div>
      </form>

      {isEditing && propertyId !== null && (
        <section className="manager-form manager-form-section image-manager-section">
          <div className="manager-section-heading">
            <div><h2>{text('managePhotos')}</h2><p>{text('imageLimitHint').replace('{count}', String(images.length))}</p></div>
            <span className="manager-count">{images.length} / 10</span>
          </div>
          {imageError && <p className="manager-inline-error" role="alert">{imageError}</p>}
          <form className="image-upload-form" onSubmit={(event) => void submitImage(event)}>
            <label className="manager-field">
              <span>{text('chooseImage')}</span>
              <input id="property-image-file" type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" onChange={chooseImage} />
            </label>
            <label className="manager-field">
              <span>{text('imageCaption')}</span>
              <input maxLength={200} value={imageCaption} onChange={(event) => setImageCaption(event.target.value)} />
            </label>
            <label className="amenity-choice image-primary-choice">
              <input type="checkbox" checked={makePrimary || images.length === 0} onChange={(event) => setMakePrimary(event.target.checked)} disabled={images.length === 0} />
              <span>{text('makePrimaryImage')}</span>
            </label>
            <button className="button button-primary" type="submit" disabled={imageBusyId !== null || images.length >= 10}>
              <Upload size={16} aria-hidden="true" />{imageBusyId === -1 ? text('uploadingImage') : text('uploadImage')}
            </button>
          </form>
          {imageLoading ? (
            <div className="listing-state" role="status"><span className="loading-spinner" />{text('loadingImages')}</div>
          ) : images.length ? (
            <div className="managed-image-grid">
              {images.map((image) => (
                <article className="managed-image-card" key={image.id}>
                  <img src={image.image} alt={image.caption || property?.title || text('propertyImage')} />
                  <div className="managed-image-meta">
                    <p>{image.caption || text('noImageCaption')}</p>
                    {image.is_primary ? (
                      <span className="manager-badge publication-published"><Star size={13} aria-hidden="true" />{text('primaryImage')}</span>
                    ) : (
                      <button type="button" className="manager-text-button" disabled={imageBusyId !== null} onClick={() => void setPrimaryImage(image.id)}>
                        <Star size={14} aria-hidden="true" />{text('setPrimaryImage')}
                      </button>
                    )}
                    <button type="button" className="manager-text-button danger-text" disabled={imageBusyId !== null} onClick={() => void removeImage(image)}>
                      <Trash2 size={14} aria-hidden="true" />{text('deleteImage')}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="manager-state manager-empty-images">
              <ImagePlus size={24} aria-hidden="true" />
              <p>{text('noManagedImages')}</p>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
