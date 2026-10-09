import { useEffect, useMemo, useState } from 'react';
import { Route, Routes } from 'react-router-dom';

import { PageLayout } from './components/PageLayout';
import { RequireAuth } from './components/RequireAuth';
import { RequireListingManager } from './components/RequireListingManager';
import { OwnerDashboardLayout } from './components/OwnerDashboardLayout';
import { HomePage } from './pages/HomePage';
import { NotFoundPage } from './pages/PhaseNoticePage';
import { PropertiesPage } from './pages/PropertiesPage';
import { PropertyDetailPage } from './pages/PropertyDetailPage';
import { ViewingRequestPage } from './pages/ViewingRequestPage';
import { AccountPage } from './pages/AccountPage';
import { FavoritesPage } from './pages/FavoritesPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { OwnerListingsPage } from './pages/OwnerListingsPage';
import { OwnerPropertyFormPage } from './pages/OwnerPropertyFormPage';
import { OwnerViewingRequestsPage } from './pages/OwnerViewingRequestsPage';
import { messages, type Locale, type MessageKey } from './i18n';

const localeStorageKey = 'habesha-homes-locale';

function initialLocale(): Locale {
  const savedLocale = window.localStorage.getItem(localeStorageKey);
  return savedLocale === 'am' ? 'am' : 'en';
}

export default function App() {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const text = useMemo(
    () => (key: MessageKey) => messages[locale][key],
    [locale],
  );

  useEffect(() => {
    document.documentElement.lang = locale;
    window.localStorage.setItem(localeStorageKey, locale);
  }, [locale]);

  return (
    <Routes>
      <Route element={<PageLayout locale={locale} onLocaleChange={setLocale} text={text} />}>
        <Route index element={<HomePage locale={locale} text={text} />} />
        <Route path="properties" element={<PropertiesPage locale={locale} text={text} />} />
        <Route path="properties/:slug" element={<PropertyDetailPage locale={locale} text={text} />} />
        <Route path="viewing-requests/new" element={<ViewingRequestPage locale={locale} text={text} />} />
        <Route path="login" element={<LoginPage text={text} />} />
        <Route path="register" element={<RegisterPage text={text} />} />
        <Route element={<RequireAuth text={text} />}>
          <Route path="account" element={<AccountPage locale={locale} text={text} />} />
          <Route path="favorites" element={<FavoritesPage locale={locale} text={text} />} />
          <Route element={<RequireListingManager text={text} />}>
            <Route element={<OwnerDashboardLayout text={text} />}>
              <Route path="owner/listings" element={<OwnerListingsPage locale={locale} text={text} />} />
              <Route path="owner/listings/new" element={<OwnerPropertyFormPage locale={locale} text={text} />} />
              <Route path="owner/listings/:id/edit" element={<OwnerPropertyFormPage locale={locale} text={text} />} />
              <Route path="owner/viewing-requests" element={<OwnerViewingRequestsPage text={text} />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage text={text} />} />
      </Route>
    </Routes>
  );
}
