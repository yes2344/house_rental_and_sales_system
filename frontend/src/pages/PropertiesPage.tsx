import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { ArrowRight, ChevronDown, ListFilter, Search, SlidersHorizontal } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import {
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
import type { HomePageProps } from './HomePage';

const PAGE_SIZE = 12;

interface FilterValues {
  listing_type: string;
  property_type: string;
  city_id: string;
}

function readFilters(params: URLSearchParams): FilterValues {
  return {
    listing_type: params.get('listing_type') ?? '',
    property_type: params.get('property_type') ?? '',
    city_id: params.get('city_id') ?? '',
  };
}

function filtersToParams(values: FilterValues): URLSearchParams {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value.trim()) {
      params.set(key, value.trim());
    }
  });
  return params;
}

function toApiFilters(params: URLSearchParams): PropertyFilters {
  const validPropertyTypes = [
    'house', 'villa', 'apartment', 'condominium', 'land',
    'office', 'shop', 'warehouse', 'commercial', 'other',
  ];
  const page = Number(params.get('page') ?? 1);
  const listingType = params.get('listing_type');
  const propertyType = params.get('property_type');
  return {
    page_size: PAGE_SIZE,
    listing_type: listingType === 'sale' || listingType === 'rent' ? listingType as ListingType : undefined,
    property_type: validPropertyTypes.includes(propertyType ?? '') ? propertyType as PropertyType : undefined,
    city_id: Number(params.get('city_id')) > 0 ? Number(params.get('city_id')) : undefined,
    ordering: '-created_at',
    page: Number.isInteger(page) && page > 1 ? page : undefined,
  };
}

export function PropertiesPage({ locale, text }: HomePageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [formValues, setFormValues] = useState(() => readFilters(searchParams));
  const [result, setResult] = useState<PaginatedResponse<PropertySummary> | null>(null);
  const [additionalProperties, setAdditionalProperties] = useState<PropertySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [moreError, setMoreError] = useState('');
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [cities, setCities] = useState<MarketplaceLocation[]>([]);
  const [cityOptionsError, setCityOptionsError] = useState('');
  const moreRequestController = useRef<AbortController | null>(null);
  const apiFilters = useMemo(() => toApiFilters(searchParams), [searchParams]);
  const currentPage = apiFilters.page ?? 1;
  const selectedCityId = Number(searchParams.get('city_id')) || 0;

  useEffect(() => {
    const controller = new AbortController();
    void getLocationsByTypes(['city', 'city_administration'], controller.signal)
      .then((options) => {
        setCities(options);
        setCityOptionsError('');
      })
      .catch(() => {
        if (!controller.signal.aborted) setCityOptionsError(text('locationLoadError'));
      });
    return () => controller.abort();
  }, [text]);

  const loadProperties = useCallback(async (signal?: AbortSignal) => {
    moreRequestController.current?.abort();
    setAdditionalProperties([]);
    setMoreError('');
    setLoadingMore(false);
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
    return () => {
      controller.abort();
      moreRequestController.current?.abort();
    };
  }, [loadProperties]);

  useEffect(() => {
    setFormValues(readFilters(searchParams));
  }, [searchParams]);

  const updateValue = (name: keyof FilterValues, value: string) => {
    setFormValues((previous) => ({ ...previous, [name]: value }));
  };

  const submitFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSearchParams(filtersToParams(formValues));
  };

  const loadMoreProperties = async () => {
    if (!result?.next || loadingMore) return;
    const controller = new AbortController();
    moreRequestController.current?.abort();
    moreRequestController.current = controller;
    const page = currentPage + Math.floor(additionalProperties.length / PAGE_SIZE) + 1;
    setLoadingMore(true);
    setMoreError('');
    try {
      const nextResult = await getProperties({ ...apiFilters, page }, controller.signal);
      if (!controller.signal.aborted) {
        setAdditionalProperties((current) => [...current, ...nextResult.results]);
      }
    } catch (requestError) {
      if (!controller.signal.aborted) setMoreError(getErrorMessage(requestError));
    } finally {
      if (!controller.signal.aborted) setLoadingMore(false);
    }
  };

  const clearFilters = () => {
    setFormValues(readFilters(new URLSearchParams()));
    setSearchParams({});
  };

  const selectCity = (cityId: number | null) => {
    const nextValues = {
      ...readFilters(searchParams),
      city_id: cityId === null ? '' : String(cityId),
    };
    setSearchParams(filtersToParams(nextValues));
  };

  const firstResult = result?.count ? (currentPage - 1) * PAGE_SIZE + 1 : 0;
  const loadedProperties = [...(result?.results ?? []), ...additionalProperties];
  const lastResult = result ? Math.min(firstResult + loadedProperties.length - 1, result.count) : 0;
  const hasMore = result !== null && Boolean(result.next) && lastResult < result.count;

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
        </div>

        <nav className="city-filter-bar" aria-label={text('filterByCity')}>
          <button
            type="button"
            className={`city-filter-chip${selectedCityId === 0 ? ' is-active' : ''}`}
            aria-pressed={selectedCityId === 0}
            onClick={() => selectCity(null)}
          >
            {text('allCities')}
          </button>
          {cities.map((city) => (
            <button
              className={`city-filter-chip${selectedCityId === city.id ? ' is-active' : ''}`}
              key={city.id}
              type="button"
              aria-pressed={selectedCityId === city.id}
              onClick={() => selectCity(city.id)}
            >
              {locale === 'am' && city.name_am ? city.name_am : city.name}
            </button>
          ))}
          {cityOptionsError && <span className="city-filter-error" role="status">{cityOptionsError}</span>}
        </nav>

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
                  {loadedProperties.map((property) => (
                    <PropertyCard key={property.id} property={property} locale={locale} text={text} />
                  ))}
                </div>
                {hasMore && (
                  <div className="show-more-listings">
                    {moreError && <p className="listing-error" role="alert">{text('listingsError')} {moreError}</p>}
                    <button className="button button-outline" type="button" onClick={() => void loadMoreProperties()} disabled={loadingMore}>
                      {loadingMore ? <><span className="loading-spinner" />{text('loadingListings')}</> : <>{text('showMoreListings')}<ChevronDown size={16} aria-hidden="true" /></>}
                    </button>
                  </div>
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
