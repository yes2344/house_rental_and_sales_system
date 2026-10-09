import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, ListFilter, MapPin, Search, SlidersHorizontal } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import { getProperties, type ListingType, type PaginatedResponse, type PropertyFilters, type PropertySummary, type PropertyType } from '../api/properties';
import { PropertyCard } from '../components/PropertyCard';
import type { HomePageProps } from './HomePage';

const PAGE_SIZE = 12;

interface FilterValues {
  search: string;
  listing_type: string;
  property_type: string;
  location: string;
  min_price: string;
  max_price: string;
  min_bedrooms: string;
  max_bedrooms: string;
  min_bathrooms: string;
  max_bathrooms: string;
  min_size: string;
  max_size: string;
  amenities: string;
  ordering: string;
}

function readFilters(params: URLSearchParams): FilterValues {
  return {
    search: params.get('search') ?? '',
    listing_type: params.get('listing_type') ?? '',
    property_type: params.get('property_type') ?? '',
    location: params.get('location') ?? '',
    min_price: params.get('min_price') ?? '',
    max_price: params.get('max_price') ?? '',
    min_bedrooms: params.get('min_bedrooms') ?? '',
    max_bedrooms: params.get('max_bedrooms') ?? '',
    min_bathrooms: params.get('min_bathrooms') ?? '',
    max_bathrooms: params.get('max_bathrooms') ?? '',
    min_size: params.get('min_size') ?? '',
    max_size: params.get('max_size') ?? '',
    amenities: params.get('amenities') ?? '',
    ordering: params.get('ordering') ?? '-created_at',
  };
}

function filtersToParams(values: FilterValues): URLSearchParams {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value.trim() && !(key === 'ordering' && value === '-created_at')) {
      params.set(key, value.trim());
    }
  });
  return params;
}

function toApiFilters(params: URLSearchParams): PropertyFilters {
  const validOrderings = ['-created_at', 'price', '-price', '-area_sqft'];
  const validPropertyTypes = ['house', 'villa', 'apartment', 'land', 'commercial'];
  const page = Number(params.get('page') ?? 1);
  const listingType = params.get('listing_type');
  const propertyType = params.get('property_type');
  const ordering = params.get('ordering');
  return {
    page_size: PAGE_SIZE,
    search: params.get('search') || undefined,
    listing_type: listingType === 'sale' || listingType === 'rent' ? listingType as ListingType : undefined,
    property_type: validPropertyTypes.includes(propertyType ?? '') ? propertyType as PropertyType : undefined,
    location: params.get('location') || undefined,
    min_price: params.get('min_price') || undefined,
    max_price: params.get('max_price') || undefined,
    min_bedrooms: params.get('min_bedrooms') || undefined,
    max_bedrooms: params.get('max_bedrooms') || undefined,
    min_bathrooms: params.get('min_bathrooms') || undefined,
    max_bathrooms: params.get('max_bathrooms') || undefined,
    min_size: params.get('min_size') || undefined,
    max_size: params.get('max_size') || undefined,
    amenities: params.get('amenities') || undefined,
    ordering: validOrderings.includes(ordering ?? '') ? ordering ?? undefined : undefined,
    page: Number.isInteger(page) && page > 1 ? page : undefined,
  };
}

export function PropertiesPage({ locale, text }: HomePageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [formValues, setFormValues] = useState(() => readFilters(searchParams));
  const [result, setResult] = useState<PaginatedResponse<PropertySummary> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterError, setFilterError] = useState(false);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const apiFilters = useMemo(() => toApiFilters(searchParams), [searchParams]);
  const currentPage = apiFilters.page ?? 1;

  const loadProperties = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError('');
    try {
      const properties = await getProperties(apiFilters, signal);
      setResult(properties);
    } catch (requestError) {
      if (signal?.aborted) return;
      setError(getErrorMessage(requestError));
      setResult(null);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [apiFilters]);

  useEffect(() => {
    const controller = new AbortController();
    void loadProperties(controller.signal);
    return () => controller.abort();
  }, [loadProperties]);

  useEffect(() => {
    setFormValues(readFilters(searchParams));
  }, [searchParams]);

  const updateValue = (name: keyof FilterValues, value: string) => {
    setFormValues((previous) => ({ ...previous, [name]: value }));
    setFilterError(false);
  };

  const submitFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const ranges: [string, string][] = [
      [formValues.min_price, formValues.max_price],
      [formValues.min_bedrooms, formValues.max_bedrooms],
      [formValues.min_bathrooms, formValues.max_bathrooms],
      [formValues.min_size, formValues.max_size],
    ];
    if (ranges.some(([minimum, maximum]) => minimum && maximum && Number(minimum) > Number(maximum))) {
      setFilterError(true);
      return;
    }
    setFilterError(false);
    setSearchParams(filtersToParams(formValues));
  };

  const goToPage = (page: number) => {
    const nextParams = new URLSearchParams(searchParams);
    if (page <= 1) nextParams.delete('page');
    else nextParams.set('page', String(page));
    setSearchParams(nextParams);
    window.scrollTo({
      top: 0,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    });
  };

  const clearFilters = () => {
    setFormValues(readFilters(new URLSearchParams()));
    setSearchParams({});
  };

  const totalPages = Math.max(1, Math.ceil((result?.count ?? 0) / PAGE_SIZE));
  const firstResult = result?.count ? (currentPage - 1) * PAGE_SIZE + 1 : 0;
  const lastResult = result ? Math.min(currentPage * PAGE_SIZE, result.count) : 0;

  return (
    <main id="main-content" className="results-page">
      <section className="results-heading">
        <div className="container">
          <div className="breadcrumbs"><Link to="/">{text('home')}</Link><span>/</span><span>{text('explore')}</span></div>
          <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text('latestEyebrow')}</p>
          <h1>{text('searchResultsTitle')}</h1>
          <p>{text('latestDescription')}</p>
        </div>
      </section>

      <section className="container results-content">
        <div className="results-toolbar">
          <div className="results-count">
            <span className="results-count-icon"><ListFilter size={17} aria-hidden="true" /></span>
            {loading ? text('loadingListings') : `${result?.count ?? 0} ${text('resultCount')}`}
          </div>
          <label className="sort-control">
            <span>{text('sortBy')}</span>
            <select
              aria-label={text('sortOption')}
              value={formValues.ordering}
              onChange={(event) => {
                const nextValues = { ...formValues, ordering: event.target.value };
                setFormValues(nextValues);
                setSearchParams(filtersToParams(nextValues));
              }}
            >
              <option value="-created_at">{text('sortNewest')}</option>
              <option value="price">{text('sortPriceLow')}</option>
              <option value="-price">{text('sortPriceHigh')}</option>
              <option value="-area_sqft">{text('sortLargest')}</option>
            </select>
          </label>
        </div>

        <div className="results-layout">
          <aside className={`filter-sidebar${filtersExpanded ? ' is-expanded' : ''}`}>
            <button
              className="filter-mobile-toggle"
              type="button"
              aria-expanded={filtersExpanded}
              onClick={() => setFiltersExpanded((expanded) => !expanded)}
            >
              <SlidersHorizontal size={16} aria-hidden="true" />
              {filtersExpanded ? text('filtersCollapse') : text('filtersExpand')}
            </button>
            <form className={`filter-form${filtersExpanded ? ' is-expanded' : ''}`} onSubmit={submitFilters}>
              <div className="filter-title-row"><h2>{text('filterProperties')}</h2><SlidersHorizontal size={17} aria-hidden="true" /></div>
              <label className="filter-label" htmlFor="filter-search">{text('searchKeyword')}</label>
              <span className="filter-search-wrap"><Search size={16} aria-hidden="true" />
                <input id="filter-search" value={formValues.search} onChange={(event) => updateValue('search', event.target.value)} placeholder={text('searchKeywordPlaceholder')} />
              </span>

              <fieldset className="filter-fieldset">
                <legend>{text('listingTypeLabel')}</legend>
                <div className="filter-choice-row">
                  <label><input type="radio" name="listing_type" value="" checked={!formValues.listing_type} onChange={() => updateValue('listing_type', '')} />{text('anyType')}</label>
                  <label><input type="radio" name="listing_type" value="sale" checked={formValues.listing_type === 'sale'} onChange={() => updateValue('listing_type', 'sale')} />{text('forSale')}</label>
                  <label><input type="radio" name="listing_type" value="rent" checked={formValues.listing_type === 'rent'} onChange={() => updateValue('listing_type', 'rent')} />{text('forRent')}</label>
                </div>
              </fieldset>

              <label className="filter-label" htmlFor="filter-type">{text('propertyType')}</label>
              <select className="filter-select" id="filter-type" value={formValues.property_type} onChange={(event) => updateValue('property_type', event.target.value)}>
                <option value="">{text('anyType')}</option>
                <option value="house">{text('house')}</option>
                <option value="apartment">{text('apartment')}</option>
                <option value="land">{text('land')}</option>
                <option value="commercial">{text('commercial')}</option>
              </select>

              <label className="filter-label" htmlFor="filter-location">{text('location')}</label>
              <span className="filter-search-wrap"><MapPin size={16} aria-hidden="true" />
                <input id="filter-location" value={formValues.location} onChange={(event) => updateValue('location', event.target.value)} placeholder={text('locationPlaceholder')} />
              </span>

              <div className="filter-price-heading">{text('priceLabel')}</div>
              <div className="filter-two-columns">
                <label className="filter-label" htmlFor="filter-min-price">{text('minimumPrice')}
                  <input id="filter-min-price" className="filter-input" type="number" min="0" step="1000" inputMode="numeric" value={formValues.min_price} onChange={(event) => updateValue('min_price', event.target.value)} />
                </label>
                <label className="filter-label" htmlFor="filter-max-price">{text('maximumPrice')}
                  <input id="filter-max-price" className="filter-input" type="number" min="0" step="1000" inputMode="numeric" value={formValues.max_price} onChange={(event) => updateValue('max_price', event.target.value)} />
                </label>
              </div>

              <div className="filter-two-columns">
                <label className="filter-label" htmlFor="filter-bedrooms">{text('minimumBedrooms')}
                  <select className="filter-select" id="filter-bedrooms" value={formValues.min_bedrooms} onChange={(event) => updateValue('min_bedrooms', event.target.value)}>
                    <option value="">{text('anyType')}</option>
                    {[1, 2, 3, 4, 5].map((count) => <option value={count} key={count}>{count}+</option>)}
                  </select>
                </label>
                <label className="filter-label" htmlFor="filter-max-bedrooms">{text('maximumBedrooms')}
                  <select className="filter-select" id="filter-max-bedrooms" value={formValues.max_bedrooms} onChange={(event) => updateValue('max_bedrooms', event.target.value)}>
                    <option value="">{text('anyType')}</option>
                    {[1, 2, 3, 4, 5].map((count) => <option value={count} key={count}>{count}</option>)}
                  </select>
                </label>
              </div>
              <div className="filter-two-columns">
                <label className="filter-label" htmlFor="filter-bathrooms">{text('minimumBathrooms')}
                  <select className="filter-select" id="filter-bathrooms" value={formValues.min_bathrooms} onChange={(event) => updateValue('min_bathrooms', event.target.value)}>
                    <option value="">{text('anyType')}</option>
                    {[1, 2, 3, 4].map((count) => <option value={count} key={count}>{count}+</option>)}
                  </select>
                </label>
                <label className="filter-label" htmlFor="filter-max-bathrooms">{text('maximumBathrooms')}
                  <select className="filter-select" id="filter-max-bathrooms" value={formValues.max_bathrooms} onChange={(event) => updateValue('max_bathrooms', event.target.value)}>
                    <option value="">{text('anyType')}</option>
                    {[1, 2, 3, 4].map((count) => <option value={count} key={count}>{count}</option>)}
                  </select>
                </label>
              </div>
              <div className="filter-two-columns">
                <label className="filter-label" htmlFor="filter-size">{text('minimumSize')}
                  <input id="filter-size" className="filter-input" type="number" min="0" step="50" inputMode="numeric" value={formValues.min_size} onChange={(event) => updateValue('min_size', event.target.value)} />
                </label>
                <label className="filter-label" htmlFor="filter-max-size">{text('maximumSize')}
                  <input id="filter-max-size" className="filter-input" type="number" min="0" step="50" inputMode="numeric" value={formValues.max_size} onChange={(event) => updateValue('max_size', event.target.value)} />
                </label>
              </div>

              <label className="filter-label" htmlFor="filter-amenities">{text('amenitiesFilter')}
                <input id="filter-amenities" className="filter-input" value={formValues.amenities} onChange={(event) => updateValue('amenities', event.target.value)} placeholder={text('amenitiesPlaceholder')} />
              </label>
              {filterError && <p className="filter-validation" role="alert">{text('invalidFilters')}</p>}
              <button className="button button-primary filter-submit" type="submit">{text('applyFilters')} <ArrowRight size={15} aria-hidden="true" /></button>
              <button className="filter-clear" type="button" onClick={clearFilters}>{text('clearFilters')}</button>
            </form>
          </aside>

          <div className="results-main">
            {loading ? (
              <div className="listing-state results-state" role="status"><span className="loading-spinner" />{text('loadingListings')}</div>
            ) : error ? (
              <div className="listing-state listing-error results-state" role="alert">
                <span>{text('listingsError')}<small>{error}</small></span>
                <button className="button button-outline" type="button" onClick={() => void loadProperties()}>{text('retry')}</button>
              </div>
            ) : result?.results.length ? (
              <>
                <div className="results-range">{firstResult}–{lastResult} {text('resultCount')}</div>
                <div className="listing-grid results-grid">
                  {result.results.map((property) => (
                    <PropertyCard key={property.id} property={property} locale={locale} text={text} />
                  ))}
                </div>
                {totalPages > 1 && (
                  <nav className="pagination" aria-label={text('pageNavigation')}>
                    <button type="button" onClick={() => goToPage(currentPage - 1)} disabled={!result.previous}>
                      <ArrowLeft size={15} aria-hidden="true" />{text('previousPage')}
                    </button>
                    <span>{text('pageOf')} <strong>{currentPage}</strong> / {totalPages}</span>
                    <button type="button" onClick={() => goToPage(currentPage + 1)} disabled={!result.next}>
                      {text('nextPage')}<ArrowRight size={15} aria-hidden="true" />
                    </button>
                  </nav>
                )}
              </>
            ) : (
              <div className="listing-empty results-empty">
                <span className="empty-icon"><Search size={22} aria-hidden="true" /></span>
                <h2>{text('noSearchResults')}</h2>
                <p>{text('adjustFilters')}</p>
                <button className="button button-outline" type="button" onClick={clearFilters}>{text('clearFilters')}</button>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
