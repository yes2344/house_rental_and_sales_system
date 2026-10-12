import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { ArrowDown, ArrowRight, ArrowUpRight, Check, House, MapPin, Search, ShieldCheck, UsersRound } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import { getLatestProperties, type PropertyLocationSuggestion, type PropertySummary } from '../api/properties';
import { PropertyCard } from '../components/PropertyCard';
import { LocationSearchInput } from '../components/LocationSearchInput';
import { useHomepageContent } from '../HomepageContentContext';
import { SocialMark, socialPlatformNames } from '../components/SocialMark';
import { useBrokerageContact } from '../BrokerageContactContext';
import type { Locale, MessageKey } from '../i18n';

export interface HomePageProps {
  locale: Locale;
  text: (key: MessageKey) => string;
}

export function HomePage({ locale, text }: HomePageProps) {
  const navigate = useNavigate();
  const { notes } = useHomepageContent();
  const { contact } = useBrokerageContact();
  const [listingType, setListingType] = useState<'sale' | 'rent'>('sale');
  const [propertyType, setPropertyType] = useState('');
  const [location, setLocation] = useState('Addis Ababa');
  const [locationId, setLocationId] = useState<number | null>(null);
  const [properties, setProperties] = useState<PropertySummary[]>([]);
  const [listingsLoading, setListingsLoading] = useState(true);
  const [listingsError, setListingsError] = useState('');

  const loadListings = useCallback(async () => {
    setListingsLoading(true);
    setListingsError('');
    try {
      setProperties(await getLatestProperties());
    } catch (error) {
      setListingsError(getErrorMessage(error));
    } finally {
      setListingsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadListings();
  }, [loadListings]);

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = new URLSearchParams({ listing_type: listingType });
    if (locationId) query.set('location_id', String(locationId));
    else if (location.trim()) query.set('location', location.trim());
    if (propertyType) query.set('property_type', propertyType);
    navigate(`/properties?${query.toString()}`);
  };

  const searchCategory = (category: string) => {
    navigate(`/properties?${new URLSearchParams({ property_type: category }).toString()}`);
  };

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
          <form className="search-panel" onSubmit={submitSearch}>
            <div className="search-panel-head">
              <div>
                <span className="search-overline"><Search size={14} aria-hidden="true" /> {text('searchLabel')}</span>
              </div>
              <div className="listing-type-toggle" role="group" aria-label={text('searchLabel')}>
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
            <div className="search-fields">
              <div className="search-field">
                <label htmlFor="home-location">{text('location')}</label>
                <LocationSearchInput
                  id="home-location"
                  value={location}
                  locale={locale}
                  placeholder={text('locationPlaceholder')}
                  onChange={(value) => {
                    setLocation(value);
                    setLocationId(null);
                  }}
                  onSelect={(selected: PropertyLocationSuggestion) => {
                    setLocation(locale === 'am' && selected.name_am ? selected.name_am : selected.name);
                    setLocationId(selected.id);
                  }}
                />
              </div>
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
              <button className="button button-primary search-submit" type="submit">
                <Search size={17} aria-hidden="true" /><span>{text('searchButton')}</span>
              </button>
            </div>
            <p className="search-note"><Check size={14} aria-hidden="true" />{text('searchNote')}</p>
          </form>
        </div>
      </section>

      <section className="trust-strip" aria-label="Marketplace features">
        <div className="container trust-inner">
          <div className="trust-item"><span className="trust-icon"><ShieldCheck size={18} aria-hidden="true" /></span>{text('promiseStatus')}</div>
          <span className="trust-divider" aria-hidden="true" />
          <div className="trust-item"><span className="trust-icon"><UsersRound size={18} aria-hidden="true" /></span>{text('promiseContact')}</div>
          <span className="trust-divider" aria-hidden="true" />
          <div className="trust-item"><span className="trust-icon"><Check size={18} aria-hidden="true" /></span>{text('promiseViewing')}</div>
        </div>
      </section>

      <section className="section owner-announcement-cta">
        <div className="container owner-announcement-cta-inner">
          <div>
            <p className="eyebrow eyebrow-muted">For property owners</p>
            <h2>Want to advertise your property?</h2>
            <p className="section-description">Submit your property details to the brokerage for review and an advertising agreement.</p>
          </div>
          <Link className="button button-primary" to="/owner/announcements">Announce your property <ArrowUpRight size={16} aria-hidden="true" /></Link>
        </div>
      </section>

      <section className="section listings-section" id="latest-listings">
        <div className="container">
          <div className="section-heading">
            <div>
              <p className="eyebrow eyebrow-muted">{text('latestEyebrow')}</p>
              <h2>{text('latestTitle')}</h2>
              <p className="section-description">{text('latestDescription')}</p>
            </div>
            <Link className="text-link desktop-only" to="/properties">{text('seeAll')} <ArrowRight size={16} aria-hidden="true" /></Link>
          </div>
          {listingsLoading ? (
            <div className="listing-state" role="status"><span className="loading-spinner" />{text('loadingListings')}</div>
          ) : listingsError ? (
            <div className="listing-state listing-error" role="alert">
              <span>{text('listingsError')} <small>{listingsError}</small></span>
              <button className="button button-outline" type="button" onClick={() => void loadListings()}>{text('retry')}</button>
            </div>
          ) : properties.length ? (
            <div className="listing-grid">
              {properties.map((property) => (
                <PropertyCard key={property.id} property={property} locale={locale} text={text} />
              ))}
            </div>
          ) : (
            <div className="listing-empty">
              <span className="empty-icon"><House size={23} aria-hidden="true" /></span>
              <p>{text('noListings')}</p>
              <Link className="text-link" to="/properties">{text('browseAll')} <ArrowRight size={16} aria-hidden="true" /></Link>
            </div>
          )}
          <Link className="text-link mobile-only" to="/properties">{text('seeAll')} <ArrowRight size={16} aria-hidden="true" /></Link>
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
                <span className="category-name">{text(item.key as MessageKey)}</span>
                <span className="category-action">{text('categorySearch')} <ArrowUpRight size={15} aria-hidden="true" /></span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {notes.length > 0 && (
        <section className="section homepage-notes-section" aria-labelledby="homepage-notes-title">
          <div className="container">
            <div className="section-heading">
              <div><p className="eyebrow eyebrow-muted">{text('brokerContactTitle')}</p><h2 id="homepage-notes-title">{text('homepageNotesTitle')}</h2></div>
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

      <section className="section process-section" id="how-it-works">
        <div className="container process-layout">
          <div className="process-intro">
            <p className="eyebrow"><span className="eyebrow-dot" />{text('processEyebrow')}</p>
            <h2>{text('processTitle')}</h2>
            <p>{text('heroBody')}</p>
            <Link className="button button-light" to="/properties">{text('explore')} <ArrowRight size={16} aria-hidden="true" /></Link>
          </div>
          <div className="process-steps">
            {[
              { number: '01', title: 'processOneTitle', body: 'processOneBody', icon: <Search size={19} aria-hidden="true" /> },
              { number: '02', title: 'processTwoTitle', body: 'processTwoBody', icon: <UsersRound size={19} aria-hidden="true" /> },
              { number: '03', title: 'processThreeTitle', body: 'processThreeBody', icon: <MapPin size={19} aria-hidden="true" /> },
            ].map((step) => (
              <article className="process-step" key={step.number}>
                <span className="step-number">{step.number}</span>
                <span className="step-icon">{step.icon}</span>
                <div><h3>{text(step.title as MessageKey)}</h3><p>{text(step.body as MessageKey)}</p></div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="closing-section">
        <div className="container closing-inner">
          <div><span className="closing-kicker">HABESHA HOMES · ADDIS ABABA</span><h2>{text('closingTitle')}</h2><p>{text('closingBody')}</p></div>
          <Link className="button button-light" to="/properties">{text('explore')} <ArrowRight size={16} aria-hidden="true" /></Link>
        </div>
      </section>
    </main>
  );
}
