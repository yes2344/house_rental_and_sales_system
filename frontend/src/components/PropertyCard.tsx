import { Bath, BedDouble, CalendarDays, Mail, MapPin, Phone, Ruler } from 'lucide-react';
import { Link } from 'react-router-dom';

import type { PropertySummary } from '../api/properties';
import type { Locale, MessageKey } from '../i18n';
import { FavoriteButton } from './FavoriteButton';
import { formatPropertyPrice, formatRegistrationDate } from './propertyDisplay';
import { formatPropertyLocation } from './locationDisplay';
import { hasPublicCoordinates, openStreetMapUrl } from './propertyLocation';
import { PropertySlideshow } from './PropertySlideshow';

interface PropertyCardProps {
  property: PropertySummary;
  locale: Locale;
  text: (key: MessageKey) => string;
}

export function PropertyCard({ property, locale, text }: PropertyCardProps) {
  const category = {
    house: text('house'),
    villa: text('house'),
    apartment: text('apartment'),
    land: text('land'),
    commercial: text('commercial'),
  }[property.category] ?? property.category;
  const price = formatPropertyPrice(
    property.price,
    property.listing_type,
    property.rental_frequency,
    locale,
    text,
  );
  const registrationDate = formatRegistrationDate(property.created_at, locale);
  const statusMessage: Record<string, MessageKey> = {
    rented: 'statusRented',
    sold: 'statusSold',
    inactive: 'statusInactive',
  };
  const statusKey = statusMessage[property.status] ?? 'available';
  const mapUrl = hasPublicCoordinates(property.latitude, property.longitude)
    ? openStreetMapUrl(Number(property.latitude), Number(property.longitude))
    : null;

  return (
    <article className="listing-card">
      <FavoriteButton propertyId={property.id} text={text} />
      <div className="listing-image-link">
        <PropertySlideshow
          images={property.images ?? []}
          fallbackImage={property.primary_image}
          title={property.title}
          fallbackLabel={text('emptyImageLabel')}
          previousLabel={text('previousPage')}
          nextLabel={text('nextPage')}
          photoLabel={text('photoNumber')}
        />
        <Link className="listing-image-target" to={`/properties/${property.slug}`}>
          <span className="visually-hidden">{property.title}</span>
        </Link>
        <span className={`listing-type ${property.listing_type === 'rent' ? 'is-rent' : ''}`}>
          {property.listing_type === 'rent' ? text('forRent') : text('forSale')}
        </span>
      </div>
      <div className="listing-card-content">
        <div className="listing-location">
          <MapPin size={14} aria-hidden="true" />
          <span>{formatPropertyLocation(property, locale)}</span>
          {mapUrl && <a href={mapUrl} target="_blank" rel="noreferrer">{text('viewOnMap')}</a>}
        </div>
        <h3><Link to={`/properties/${property.slug}`}>{property.title}</Link></h3>
        <div className="listing-specs" aria-label={`${category} specifications`}>
          {property.bedrooms > 0 && <span><BedDouble size={15} aria-hidden="true" />{property.bedrooms} {text('bedrooms')}</span>}
          {property.bathrooms > 0 && <span><Bath size={15} aria-hidden="true" />{property.bathrooms} {text('bathrooms')}</span>}
          {property.area_sqft > 0 && <span><Ruler size={15} aria-hidden="true" />{property.area_sqft.toLocaleString(locale === 'am' ? 'am-ET' : 'en-ET')} {text('area')}</span>}
        </div>
        {registrationDate && (
          <p className="listing-registration-date">
            <CalendarDays size={13} aria-hidden="true" />{text('registeredDate')} {registrationDate}
          </p>
        )}
        {(property.public_contact_phone || property.public_contact_email) && (
          <div className="listing-contact" aria-label={text('contactHeading')}>
            {property.public_contact_phone && (
              <a href={`tel:${property.public_contact_phone}`} aria-label={`${text('contactByPhone')}: ${property.public_contact_phone}`}>
                <Phone size={13} aria-hidden="true" /><span>{property.public_contact_phone}</span>
              </a>
            )}
            {property.public_contact_email && (
              <a href={`mailto:${property.public_contact_email}`} aria-label={`${text('contactByEmail')}: ${property.public_contact_email}`}>
                <Mail size={13} aria-hidden="true" /><span>{property.public_contact_email}</span>
              </a>
            )}
          </div>
        )}
        <div className="listing-card-bottom">
          <strong className="listing-price">{price}</strong>
          <span className={`listing-status${statusKey === 'available' ? '' : ' is-unavailable'}`}><span />{text(statusKey)}</span>
        </div>
      </div>
    </article>
  );
}
