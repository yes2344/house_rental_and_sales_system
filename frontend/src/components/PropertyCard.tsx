import { Bath, BedDouble, MapPin, Ruler } from 'lucide-react';
import { Link } from 'react-router-dom';

import type { PropertySummary } from '../api/properties';
import type { Locale, MessageKey } from '../i18n';
import { FavoriteButton } from './FavoriteButton';
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
  const price = new Intl.NumberFormat(locale === 'am' ? 'am-ET' : 'en-ET', {
    maximumFractionDigits: 0,
  }).format(Number(property.price));
  const statusMessage: Record<string, MessageKey> = {
    rented: 'statusRented',
    sold: 'statusSold',
    inactive: 'statusInactive',
  };
  const statusKey = statusMessage[property.status] ?? 'available';

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
        <div className="listing-location"><MapPin size={14} aria-hidden="true" />{property.location}</div>
        <h3><Link to={`/properties/${property.slug}`}>{property.title}</Link></h3>
        <div className="listing-specs" aria-label={`${category} specifications`}>
          {property.bedrooms > 0 && <span><BedDouble size={15} aria-hidden="true" />{property.bedrooms} {text('bedrooms')}</span>}
          {property.bathrooms > 0 && <span><Bath size={15} aria-hidden="true" />{property.bathrooms} {text('bathrooms')}</span>}
          {property.area_sqft > 0 && <span><Ruler size={15} aria-hidden="true" />{property.area_sqft.toLocaleString(locale === 'am' ? 'am-ET' : 'en-ET')} {text('area')}</span>}
        </div>
        <div className="listing-card-bottom">
          <strong className="listing-price"><span>{text('ethiopianBirr')}</span> {price}</strong>
          <span className={`listing-status${statusKey === 'available' ? '' : ' is-unavailable'}`}><span />{text(statusKey)}</span>
        </div>
      </div>
    </article>
  );
}
