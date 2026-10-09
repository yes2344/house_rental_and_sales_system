import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { ArrowLeft, ArrowRight, Bath, BedDouble, CalendarDays, Check, Mail, MapPin, Phone, Ruler, Share2 } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import { getProperty, type PropertyDetail } from '../api/properties';
import { FavoriteButton } from '../components/FavoriteButton';
import { PropertyPhoto } from '../components/PropertyPhoto';
import type { MessageKey } from '../i18n';
import type { HomePageProps } from './HomePage';

export function PropertyDetailPage({ locale, text }: HomePageProps) {
  const { slug = '' } = useParams();
  const [property, setProperty] = useState<PropertyDetail | null>(null);
  const [selectedImage, setSelectedImage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [shareMessage, setShareMessage] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setProperty(null);
    setError('');
    setNotFound(false);
    setSelectedImage(0);
    getProperty(slug, controller.signal)
      .then(setProperty)
      .catch((requestError: unknown) => {
        if (controller.signal.aborted) return;
        setNotFound(axios.isAxiosError(requestError) && requestError.response?.status === 404);
        setError(getErrorMessage(requestError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [slug]);

  const galleryImages = useMemo(() => {
    if (!property) return [];
    const listedImages = property.images.filter((image) => image.url);
    const orderedImages = [...listedImages].sort((first, second) => Number(second.is_primary) - Number(first.is_primary));
    if (orderedImages.length) return orderedImages;
    if (property.primary_image) {
      return [{ id: property.id, url: property.primary_image, caption: '', is_primary: true }];
    }
    return [];
  }, [property]);

  const formatPrice = (price: string) => new Intl.NumberFormat(locale === 'am' ? 'am-ET' : 'en-ET', {
    maximumFractionDigits: 0,
  }).format(Number(price));

  const shareProperty = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareMessage(text('shareSuccess'));
    } catch {
      setShareMessage(text('shareError'));
    }
  };

  if (loading) {
    return <main className="detail-state-page" id="main-content"><div className="listing-state" role="status"><span className="loading-spinner" />{text('loadingListings')}</div></main>;
  }

  if (!property) {
    return (
      <main className="detail-state-page" id="main-content">
        <div className="listing-state detail-error" role="alert">
          <span>{notFound ? text('propertyNotFound') : text('listingsError')}<small>{notFound ? text('listingUnavailable') : error}</small></span>
          <div className="detail-error-actions">
            {!notFound && <button className="button button-outline" type="button" onClick={() => window.location.reload()}>{text('refresh')}</button>}
            <Link className="button button-primary" to="/properties"><ArrowLeft size={15} aria-hidden="true" />{text('backToProperties')}</Link>
          </div>
        </div>
      </main>
    );
  }

  const categoryKey: Record<string, MessageKey> = {
    house: 'house',
    villa: 'house',
    apartment: 'apartment',
    land: 'land',
    commercial: 'commercial',
  };
  const image = galleryImages[selectedImage];
  const formattedUpdatedDate = new Intl.DateTimeFormat(locale === 'am' ? 'am-ET' : 'en-ET', {
    dateStyle: 'medium',
  }).format(new Date(property.updated_at));

  return (
    <main id="main-content" className="detail-page">
      <section className="detail-heading container">
        <div className="breadcrumbs"><Link to="/">{text('home')}</Link><span>/</span><Link to="/properties">{text('explore')}</Link><span>/</span><span>{property.title}</span></div>
        <Link className="back-link" to="/properties"><ArrowLeft size={15} aria-hidden="true" />{text('backToProperties')}</Link>
        <div className="detail-title-row">
          <div><p className="detail-location"><MapPin size={15} aria-hidden="true" />{property.location}</p><h1>{property.title}</h1></div>
          <div className="detail-actions">
            <FavoriteButton propertyId={property.id} text={text} variant="detail" />
            <button className="share-button" type="button" onClick={() => void shareProperty()}><Share2 size={15} aria-hidden="true" />{text('shareProperty')}</button>
          </div>
        </div>
        {shareMessage && <p className="share-feedback" role="status">{shareMessage}</p>}
      </section>

      <section className="container detail-gallery-section" aria-label={text('photos')}>
        {galleryImages.length ? (
          <div className="detail-gallery">
            <div className="detail-main-image">
              <PropertyPhoto
                src={image?.url}
                alt={`${image?.caption || text('propertyImage')}: ${property.title}`}
                className="detail-property-image"
                fallbackClassName="detail-main-image-placeholder"
                fallbackLabel={text('noPhoto')}
              />
              <span className={`listing-type ${property.listing_type === 'rent' ? 'is-rent' : ''}`}>
                {property.listing_type === 'rent' ? text('forRent') : text('forSale')}
              </span>
              {galleryImages.length > 1 && (
                <>
                  <button className="gallery-arrow gallery-previous" type="button" aria-label={text('previousPage')} onClick={() => setSelectedImage((selectedImage - 1 + galleryImages.length) % galleryImages.length)}><ArrowLeft size={19} /></button>
                  <button className="gallery-arrow gallery-next" type="button" aria-label={text('nextPage')} onClick={() => setSelectedImage((selectedImage + 1) % galleryImages.length)}><ArrowRight size={19} /></button>
                  <span className="gallery-count">{selectedImage + 1} / {galleryImages.length}</span>
                </>
              )}
            </div>
            {galleryImages.length > 1 && (
              <div className="gallery-thumbnails">
                {galleryImages.map((galleryImage, index) => (
                  <button className={`gallery-thumbnail${selectedImage === index ? ' is-selected' : ''}`} key={galleryImage.id} type="button" aria-label={`${text('photoNumber')} ${index + 1}`} aria-pressed={selectedImage === index} onClick={() => setSelectedImage(index)}>
                    <PropertyPhoto
                      src={galleryImage.url}
                      alt=""
                      className="gallery-thumbnail-image"
                      fallbackClassName="gallery-thumbnail-placeholder"
                      fallbackLabel={text('emptyImageLabel')}
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="detail-no-photo"><span>{text('noPhoto')}</span></div>
        )}
      </section>

      <section className="container detail-content-layout">
        <div className="detail-primary-content">
          <div className="detail-price-row">
            <div className="detail-price"><span>{text('priceLabel')}</span><strong>{text('ethiopianBirr')} {formatPrice(property.price)}</strong></div>
            <span className="detail-availability"><span />{text('available')}</span>
          </div>
          <section className="detail-section">
            <h2>{text('specifications')}</h2>
            <div className="detail-spec-grid">
              <div className="detail-spec"><span className="detail-spec-icon"><BedDouble size={19} aria-hidden="true" /></span><span><small>{text('bedrooms')}</small><strong>{property.bedrooms}</strong></span></div>
              <div className="detail-spec"><span className="detail-spec-icon"><Bath size={19} aria-hidden="true" /></span><span><small>{text('bathrooms')}</small><strong>{property.bathrooms}</strong></span></div>
              <div className="detail-spec"><span className="detail-spec-icon"><Ruler size={19} aria-hidden="true" /></span><span><small>{text('sizeLabel')}</small><strong>{property.area_sqft.toLocaleString(locale === 'am' ? 'am-ET' : 'en-ET')} {text('area')}</strong></span></div>
              <div className="detail-spec"><span className="detail-spec-icon"><MapPin size={19} aria-hidden="true" /></span><span><small>{text('categoryLabel')}</small><strong>{text(categoryKey[property.category] ?? 'house')}</strong></span></div>
            </div>
          </section>
          <section className="detail-section detail-description">
            <h2>{text('detailsHeading')}</h2>
            <p>{property.description || text('descriptionUnavailable')}</p>
            {property.features && <p className="detail-features">{property.features}</p>}
          </section>
          {property.amenities.length > 0 && (
            <section className="detail-section">
              <h2>{text('amenitiesHeading')}</h2>
              <ul className="amenity-list">
                {property.amenities.map((amenity) => <li key={amenity.id}><Check size={14} aria-hidden="true" />{locale === 'am' && amenity.name_am ? amenity.name_am : amenity.name}</li>)}
              </ul>
            </section>
          )}
          <p className="detail-updated"><CalendarDays size={14} aria-hidden="true" />{text('lastUpdated')} {formattedUpdatedDate}</p>
        </div>

        <aside className="contact-card">
          <p className="eyebrow eyebrow-muted">{text('contactHeading')}</p>
          <h2>{text('contactPerson')}</h2>
          {property.contact_name && <p className="contact-name">{property.contact_name}</p>}
          {property.contact_phone && (
            <a className="contact-method" href={`tel:${property.contact_phone}`}><Phone size={17} aria-hidden="true" /><span><small>{text('contactByPhone')}</small><strong>{property.contact_phone}</strong></span></a>
          )}
          {property.contact_email && (
            <a className="contact-method" href={`mailto:${property.contact_email}`}><Mail size={17} aria-hidden="true" /><span><small>{text('contactByEmail')}</small><strong>{property.contact_email}</strong></span></a>
          )}
          <Link className="button button-primary viewing-cta" to={`/viewing-requests/new?property_id=${property.id}&property_slug=${encodeURIComponent(property.slug)}`}><CalendarDays size={16} aria-hidden="true" />{text('requestViewing')}</Link>
          <p className="contact-note">{text('viewingNoAccount')}</p>
        </aside>
      </section>
    </main>
  );
}
