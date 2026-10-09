import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';

import { useAuth } from '../AuthContext';
import { getErrorMessage } from '../api/client';
import type { Locale, MessageKey } from '../i18n';

interface HeaderProps {
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  preferenceError: string;
  text: (key: MessageKey) => string;
}

export function Header({ locale, onLocaleChange, preferenceError, text }: HeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  const [loggingOut, setLoggingOut] = useState(false);
  const { account, authLoading, signOut } = useAuth();
  const canManageListings = Boolean(account?.is_platform_owner || account?.management_permissions.some(
    (permission) => [
      'properties.view_all',
      'properties.moderate',
      'properties.edit_all',
      'properties.manage_assigned',
    ].includes(permission),
  ));
  const closeMenu = () => setMenuOpen(false);
  const logout = () => {
    setLogoutError('');
    setLoggingOut(true);
    void signOut()
      .then(() => {
        closeMenu();
        setLoggingOut(false);
      })
      .catch((error: unknown) => {
        setLogoutError(getErrorMessage(error));
        setLoggingOut(false);
      });
  };

  return (
    <>
      <a className="skip-link" href="#main-content">{text('skipToContent')}</a>
      <header className="site-header">
        <div className="container header-inner">
          <Link className="brand" to="/" aria-label={text('brandLabel')} onClick={closeMenu}>
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 36 36" fill="none">
                <path d="M5 17.1 18 6l13 11.1v12.1H5V17.1Z" fill="currentColor" />
                <path d="m3 17.4 15-13 15 13" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M15 20h6v9h-6z" fill="#F8F8F4" />
              </svg>
            </span>
            <span className="brand-copy">
              <strong>habesha<span>homes</span></strong>
              <small>DEBRE MARKOS</small>
            </span>
          </Link>

          <button
            className="menu-toggle"
            type="button"
            aria-label={menuOpen ? text('mobileMenuClose') : text('mobileMenuOpen')}
            aria-expanded={menuOpen}
            aria-controls="primary-navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={21} /> : <Menu size={21} />}
          </button>

          <nav
            className={`primary-navigation${menuOpen ? ' is-open' : ''}`}
            id="primary-navigation"
            aria-label={text('primaryNavigation')}
          >
            <NavLink to="/" end onClick={closeMenu}>{text('home')}</NavLink>
            <NavLink to="/properties" onClick={closeMenu}>{text('explore')}</NavLink>
            <NavLink to="/settings" onClick={closeMenu}>{text('settingsTitle')}</NavLink>
            <a href="/#how-it-works" onClick={closeMenu}>{text('howItWorks')}</a>
          </nav>

          <div className={`header-actions${menuOpen ? ' is-open' : ''}`}>
            <button
              type="button"
              className="language-toggle"
              onClick={() => onLocaleChange(locale === 'en' ? 'am' : 'en')}
              aria-label={locale === 'en' ? text('switchLocale') : text('switchLocaleToEnglish')}
            >
              {text('localeName')}
            </button>
            {authLoading ? (
              <span className="header-account-check">{text('loadingAccount')}</span>
            ) : account ? (
              <>
                <Link className="header-sign-in" to="/account" onClick={closeMenu}>{text('myAccount')}</Link>
                <Link className="header-sign-in" to="/favorites" onClick={closeMenu}>{text('savedHomesShort')}</Link>
                <button className="header-sign-in header-logout" type="button" disabled={loggingOut} onClick={logout}>
                  {loggingOut ? text('signingOut') : text('signOut')}
                </button>
              </>
            ) : (
              <Link className="header-sign-in" to="/login" onClick={closeMenu}>{text('signIn')}</Link>
            )}
            {canManageListings && (
              <Link className="button button-small button-primary" to="/management/listings" onClick={closeMenu}>
                {text('managerListings')}
              </Link>
            )}
            {logoutError && <span className="header-action-error" role="alert">{logoutError}</span>}
            {preferenceError && <span className="header-action-error" role="alert">{preferenceError}</span>}
          </div>
        </div>
      </header>
    </>
  );
}
