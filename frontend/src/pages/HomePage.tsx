import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { ArrowDown, ArrowUpRight, Check, ChevronDown, House, MapPin, Search } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import {
  getLocations,
  getLocationsByTypes,
  getProperties,
  type ListingType,
  type MarketplaceLocation,
  type PaginatedResponse,
  type PropertyFilters,
  type PropertySummary,
  type PropertyType,
} from '../api/properties';
import { PropertyCard } from '../components/PropertyCard';
import { useHomepageContent } from '../HomepageContentContext';
import { SocialMark, socialPlatformNames } from '../components/SocialMark';
import { useBrokerageContact } from '../BrokerageContactContext';
import type { Locale, MessageKey } from '../i18n';

export interface HomePageProps {
  locale: Locale;
  text: (key: MessageKey) => string;
}

export function HomePage({ locale, text }: HomePageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const { notes } = useHomepageContent();
  const { contact } = useBrokerageContact();
  const [listingType, setListingType] = useState('');
  const [propertyType, setPropertyType] = useState('');
  const [ordering, setOrdering] = useState('-created_at');
  const [locationId, setLocationId] = useState<number | null>(null);
  const [cityId, setCityId] = useState<number | null>(null);
  const [cities, setCities] = useState<MarketplaceLocation[]>([]);
  const [subcities, setSubcities] = useState<MarketplaceLocation[]>([]);
  const [locationOptionsError, setLocationOptionsError] = useState('');
  const [result, setResult] = useState<PaginatedResponse<PropertySummary> | null>(null);
  const [additionalProperties, setAdditionalProperties] = useState<PropertySummary[]>([]);
  const [listingsLoading, setListingsLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [listingsError, setListingsError] = useState('');
  const [moreError, setMoreError] = useState('');
  const moreRequestController = useRef<AbortController | null>(null);
  const apiFilters = useMemo<PropertyFilters>(() => {
    const validPropertyTypes: PropertyType[] = [
      'house', 'villa', 'apartment', 'condominium', 'land',
      'office', 'shop', 'warehouse', 'commercial', 'other',
    ];
    const listingTypeParam = searchParams.get('listing_type');
    const propertyTypeParam = searchParams.get('property_type');
    const orderingParam = searchParams.get('ordering');
    const locationIdParam = Number(searchParams.get('location_id'));
    const cityIdParam = Number(searchParams.get('city_id'));
    const locationParam = searchParams.get('location')?.trim();
    return {
      page_size: 12,
      ordering: orderingParam && ['-created_at', 'price', '-price', '-area_sqft'].includes(orderingParam)
        ? orderingParam
        : '-created_at',
      listing_type: listingTypeParam === 'sale' || listingTypeParam === 'rent'
        ? listingTypeParam as ListingType
        : undefined,
      property_type: validPropertyTypes.includes(propertyTypeParam as PropertyType)
        ? propertyTypeParam as PropertyType
        : undefined,
      location_id: Number.isInteger(locationIdParam) && locationIdParam > 0 ? locationIdParam : undefined,
      city_id: Number.isInteger(cityIdParam) && cityIdParam > 0 ? cityIdParam : undefined,
      location: !locationIdParam && locationParam ? locationParam : undefined,
    };
  }, [searchParams]);

  const loadListings = useCallback(async () => {
    moreRequestController.current?.abort();
    setAdditionalProperties([]);
    setMoreError('');
    setListingsLoading(true);
    setListingsError('');
    try {
      setResult(await getProperties(apiFilters));
    } catch (error) {
      setListingsError(getErrorMessage(error));
      setResult(null);
    } finally {
      setListingsLoading(false);
    }
  }, [apiFilters]);

  useEffect(() => {
    const controller = new AbortController();
    moreRequestController.current?.abort();
    setAdditionalProperties([]);
    setMoreError('');
    setListingsLoading(true);
    setListingsError('');
    void getProperties(apiFilters, controller.signal)
      .then(setResult)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setListingsError(getErrorMessage(error));
          setResult(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setListingsLoading(false);
      });
    return () => {
      controller.abort();
      moreRequestController.current?.abort();
    };
  }, [apiFilters]);

  useEffect(() => {
    setListingType(searchParams.get('listing_type') ?? '');
    setPropertyType(searchParams.get('property_type') ?? '');
    setOrdering(searchParams.get('ordering') ?? '-created_at');
    const selectedLocation = Number(searchParams.get('location_id')) || null;
    setLocationId(selectedLocation);
    setCityId(Number(searchParams.get('city_id')) || null);
  }, [searchParams]);

  const updateResults = (updates: {
    listing_type?: string;
    property_type?: string;
    location?: string;
    location_id?: number | null;
    city_id?: number | null;
  }) => {
    const next = new URLSearchParams(searchParams);
    next.delete('page');
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === undefined || value === '') next.delete(key);
      else next.set(key, String(value));
    }
    setSearchParams(next);
  };

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const next = new URLSearchParams();
    if (listingType) next.set('listing_type', listingType);
    if (propertyType) next.set('property_type', propertyType);
    if (ordering !== '-created_at') next.set('ordering', ordering);
    if (locationId) next.set('location_id', String(locationId));
    if (cityId) next.set('city_id', String(cityId));
    setSearchParams(next);
    document.getElementById('latest-listings')?.scrollIntoView({ behavior: 'smooth' });
  };

  const searchCategory = (category: string) => {
    setPropertyType(category);
    updateResults({ property_type: category });
    document.getElementById('latest-listings')?.scrollIntoView({ behavior: 'smooth' });
  };

  const clearFilters = () => {
    setListingType('');
    setPropertyType('');
    setLocationId(null);
    setCityId(null);
    setSubcities([]);
    setSearchParams({});
  };

  const loadMoreListings = async () => {
    if (!result?.next || loadingMore) return;
    const controller = new AbortController();
    moreRequestController.current?.abort();
    moreRequestController.current = controller;
    setLoadingMore(true);
    setMoreError('');
    try {
      const nextResult = await getProperties(
        { ...apiFilters, page: 2 + Math.floor(additionalProperties.length / 12) },
        controller.signal,
      );
      if (!controller.signal.aborted) {
        setAdditionalProperties((current) => [...current, ...nextResult.results]);
      }
    } catch (error: unknown) {
      if (!controller.signal.aborted) setMoreError(getErrorMessage(error));
    } finally {
      if (!controller.signal.aborted) setLoadingMore(false);
    }
  };

  const properties = [...(result?.results ?? []), ...additionalProperties];
  const hasMoreListings = Boolean(result?.next) && properties.length < (result?.count ?? 0);

  useEffect(() => {
    const controller = new AbortController();
    void getLocationsByTypes(['city', 'city_administration'], controller.signal)
      .then((items) => {
        setCities(items);
        setLocationOptionsError('');
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setLocationOptionsError(getErrorMessage(error));
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    setSubcities([]);
    if (!cityId) return;
    const controller = new AbortController();
    void getLocations(cityId, controller.signal, false, 'subcity')
      .then((items) => {
        setSubcities(items);
        setLocationOptionsError('');
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setLocationOptionsError(getErrorMessage(error));
      });
    return () => controller.abort();
  }, [cityId]);

  return (
    <main id="main-content">
      <section className="hero-section">
        <div className="container hero-grid">
          <div className="hero-copy">
            <p className="eyebrow"><span className="eyebrow-dot" />{text('heroEyebrow')}</p>
            <h1>{text('heroTitle')}</h1>
            <p className="hero-description">{text('heroBody')}</p>
            <a className="hero-scroll-link" href="#latest-listings">
              <span className="scroll-icon"><ArrowDown size={15} aria-hidden="true" /></span>
              <span>{text('explore')}</span>
            </a>
          </div>
          <div className="hero-visual">
            <img src="/addis-ababa-hills.svg" alt={text('heroArt')} />
            <div className="hero-note">
              <span className="hero-note-icon"><MapPin size={16} aria-hidden="true" /></span>
              <span><strong>{text('illustrationCity')}</strong><small>Ethiopia · ኢትዮጵያ</small></span>
            </div>
            <div className="hero-image-caption">{text('illustrationCaption')}</div>
          </div>
        </div>
      </section>

      <section className="section category-section">
        <div className="container">
          <div className="section-heading category-heading">
            <div>
              <p className="eyebrow eyebrow-muted">{text('categoryEyebrow')}</p>
              <h2>{text('categoryTitle')}</h2>
              <p className="section-description">{text('categoryDescription')}</p>
            </div>
          </div>
          <div className="category-grid">
            {[
              { key: 'house', type: 'house', symbol: '01' },
              { key: 'apartment', type: 'apartment', symbol: '02' },
              { key: 'land', type: 'land', symbol: '03' },
              { key: 'commercial', type: 'commercial', symbol: '04' },
            ].map((item) => (
              <button className="category-card" type="button" key={item.type} onClick={() => searchCategory(item.type)}>
                <span className="category-number">{item.symbol}</span>
                <span className="category-icon"><House size={22} strokeWidth={1.6} aria-hidden="true" /></span>
                <span className="category-copy">
                  <span className="category-name">{text(item.key as MessageKey)}</span>
                  <span className="category-action">{text('categorySearch')} <ArrowUpRight size={15} aria-hidden="true" /></span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="home-search-section">
        <div className="container">
          <form className="search-panel" onSubmit={submitSearch}>
            <div className="search-panel-head">
              <div>
                <span className="search-overline"><Search size={14} aria-hidden="true" /> {text('searchLabel')}</span>
              </div>
              <div className="listing-type-toggle" role="group" aria-label={text('searchLabel')}>
                <button
                  type="button"
                  className={!listingType ? 'is-active' : ''}
                  aria-pressed={!listingType}
                  onClick={() => setListingType('')}
                >{text('anyType')}</button>
                <button
                  type="button"
                  className={listingType === 'sale' ? 'is-active' : ''}
                  aria-pressed={listingType === 'sale'}
                  onClick={() => setListingType('sale')}
                >{text('searchBuy')}</button>
                <button
                  type="button"
                  className={listingType === 'rent' ? 'is-active' : ''}
                  aria-pressed={listingType === 'rent'}
                  onClick={() => setListingType('rent')}
                >{text('searchRent')}</button>
              </div>
            </div>
            <div className={`search-fields${cityId ? ' has-subcity' : ''}`}>
              <div className="search-field">
                <label htmlFor="home-city">{text('locationCity')}</label>
                <select
                  id="home-city"
                  value={cityId ?? ''}
                  onChange={(event) => {
                    const selectedCityId = Number(event.target.value) || null;
                    setCityId(selectedCityId);
                    setLocationId(null);
                    setSubcities([]);
                  }}
                >
                  <option value="">{text('chooseCity')}</option>
                  {cities.map((city) => (
                    <option key={city.id} value={city.id}>
                      {locale === 'am' && city.name_am ? city.name_am : city.name}
                    </option>
                  ))}
                </select>
              </div>
              {cityId && (
                <label className="search-field search-field-subcity">
                  <span>{text('locationSubcity')}</span>
                  <select
                    value={locationId ?? ''}
                    onChange={(event) => setLocationId(Number(event.target.value) || null)}
                    disabled={!subcities.length}
                  >
                    <option value="">{text('allAreas')}</option>
                    {subcities.map((subcity) => (
                      <option key={subcity.id} value={subcity.id}>
                        {locale === 'am' && subcity.name_am ? subcity.name_am : subcity.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label className="search-field search-field-type">
                <span>{text('propertyType')}</span>
                <select value={propertyType} onChange={(event) => setPropertyType(event.target.value)}>
                  <option value="">{text('anyType')}</option>
                  <option value="house">{text('house')}</option>
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
              </label>
              <label className="search-field search-field-ordering">
                <span>{text('sortBy')}</span>
                <select value={ordering} onChange={(event) => setOrdering(event.target.value)}>
                  <option value="-created_at">{text('sortNewest')}</option>
                  <option value="price">{text('sortPriceLow')}</option>
                  <option value="-price">{text('sortPriceHigh')}</option>
                  <option value="-area_sqft">{text('sortLargest')}</option>
                </select>
              </label>
              <button className="button button-primary search-submit" type="submit">
                <Search size={17} aria-hidden="true" /><span>{text('searchButton')}</span>
              </button>
            </div>
            {locationOptionsError
              ? <p className="search-note" role="status">{text('locationLoadError')} {locationOptionsError}</p>
              : <p className="search-note"><Check size={14} aria-hidden="true" />{text('searchNote')}</p>}
          </form>
        </div>
      </section>

      <section className="section listings-section" id="latest-listings">
        <div className="container">
          <div className="section-heading">
            <div>
              <p className="eyebrow eyebrow-muted">{text('latestEyebrow')}</p>
              <h2>{text('latestTitle')}</h2>
              <p className="section-description">
                {listingsLoading ? text('loadingListings') : `${result?.count ?? 0} ${text('resultCount')}`}
              </p>
            </div>
            <button className="filter-clear" type="button" onClick={clearFilters}>{text('clearFilters')}</button>
          </div>
          {listingsLoading ? (
            <div className="listing-state" role="status"><span className="loading-spinner" />{text('loadingListings')}</div>
          ) : listingsError ? (
            <div className="listing-state listing-error" role="alert">
              <span>{text('listingsError')} <small>{listingsError}</small></span>
              <button className="button button-outline" type="button" onClick={() => void loadListings()}>{text('retry')}</button>
            </div>
          ) : properties.length ? (
            <>
              <div className="listing-grid">
                {properties.map((property) => (
                  <PropertyCard key={property.id} property={property} locale={locale} text={text} />
                ))}
              </div>
              {hasMoreListings && (
                <div className="show-more-listings">
                  {moreError && <p className="listing-error" role="alert">{text('listingsError')} {moreError}</p>}
                  <button className="button button-outline" type="button" onClick={() => void loadMoreListings()} disabled={loadingMore}>
                    {loadingMore
                      ? <><span className="loading-spinner" />{text('loadingListings')}</>
                      : <>{text('showMoreListings')}<ChevronDown size={16} aria-hidden="true" /></>}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="listing-empty">
              <span className="empty-icon"><House size={23} aria-hidden="true" /></span>
              <h2>{text('noSearchResults')}</h2>
              <p>{text('adjustFilters')}</p>
              <button className="button button-outline" type="button" onClick={clearFilters}>{text('clearFilters')}</button>
            </div>
          )}
        </div>
      </section>

      {notes.length > 0 && (
        <section className="section homepage-notes-section" aria-labelledby="homepage-notes-title">
          <div className="container">
            <div className="section-heading">
              <div><h2 id="homepage-notes-title">{text('homepageNotesTitle')}</h2></div>
            </div>
            <div className="homepage-notes-grid">
              {notes.map((note) => (
                <article className="homepage-note-card" key={note.id}>
                  {note.title && <h3>{note.title}</h3>}
                  <p>{note.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      )}

      {contact.social_links.some((link) => link.is_enabled && link.url) && (
        <section className="homepage-social-section" aria-label={text('brokerSocialLinks')}>
          <div className="container homepage-social-inner">
            <h2>{text('brokerSocialLinks')}</h2>
            <div className="footer-socials">
              {contact.social_links.filter((link) => link.is_enabled && link.url).map((link) => (
                <a
                  key={link.platform}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={socialPlatformNames[link.platform]}
                  title={socialPlatformNames[link.platform]}
                >
                  <SocialMark platform={link.platform} />
                </a>
              ))}
            </div>
          </div>
        </section>
      )}

    </main>
  );
}
