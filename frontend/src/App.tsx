import { useMemo } from 'react';
import { Route, Routes } from 'react-router-dom';

import { BrokerageContactProvider } from './BrokerageContactContext';
import { HomepageContentProvider } from './HomepageContentContext';
import { PageLayout } from './components/PageLayout';
import { RequireAuth } from './components/RequireAuth';
import { RequireListingManager } from './components/RequireListingManager';
import { OwnerDashboardLayout } from './components/OwnerDashboardLayout';
import { HomePage } from './pages/HomePage';
import { NotFoundPage } from './pages/PhaseNoticePage';
import { PropertiesPage } from './pages/PropertiesPage';
import { PropertyDetailPage } from './pages/PropertyDetailPage';
import { ViewingRequestPage } from './pages/ViewingRequestPage';
import { ViewingRequestStatusPage } from './pages/ViewingRequestStatusPage';
import { AccountPage } from './pages/AccountPage';
import { FavoritesPage } from './pages/FavoritesPage';
import { LoginPage } from './pages/LoginPage';
import { InvitationAcceptPage } from './pages/InvitationAcceptPage';
import { RegisterPage } from './pages/RegisterPage';
import { OwnerListingsPage } from './pages/OwnerListingsPage';
import { OwnerPropertyFormPage } from './pages/OwnerPropertyFormPage';
import { OwnerViewingRequestsPage } from './pages/OwnerViewingRequestsPage';
import { BrokerageSettingsPage } from './pages/BrokerageSettingsPage';
import { SettingsPage } from './pages/SettingsPage';
import { usePreferences } from './PreferencesContext';
import { messages, type MessageKey } from './i18n';

export default function App() {
  const { preferences, preferencesError, savePreferences } = usePreferences();
  const { locale } = preferences;
  const text = useMemo(
    () => (key: MessageKey) => messages[locale][key],
    [locale],
  );

  return (
    <BrokerageContactProvider>
    <HomepageContentProvider>
    <Routes>
      <Route
        element={(
          <PageLayout
            locale={locale}
            onLocaleChange={(nextLocale) => {
              void savePreferences({ locale: nextLocale }).catch(() => undefined);
            }}
            preferenceError={preferencesError}
            text={text}
          />
        )}
      >
        <Route index element={<HomePage locale={locale} text={text} />} />
        <Route path="properties" element={<PropertiesPage locale={locale} text={text} />} />
        <Route path="properties/:slug" element={<PropertyDetailPage locale={locale} text={text} />} />
        <Route path="viewing-requests/new" element={<ViewingRequestPage locale={locale} text={text} />} />
        <Route path="viewing-requests/status" element={<ViewingRequestStatusPage text={text} />} />
        <Route path="login" element={<LoginPage text={text} />} />
        <Route path="accept-invitation" element={<InvitationAcceptPage text={text} />} />
        <Route path="register" element={<RegisterPage text={text} />} />
        <Route path="settings" element={<SettingsPage text={text} />} />
        <Route element={<RequireAuth text={text} />}>
          <Route path="account" element={<AccountPage locale={locale} text={text} />} />
          <Route path="favorites" element={<FavoritesPage locale={locale} text={text} />} />
          <Route element={<RequireListingManager text={text} />}>
            <Route element={<OwnerDashboardLayout text={text} />}>
          <Route path="management/listings" element={<OwnerListingsPage locale={locale} text={text} />} />
          <Route path="management/listings/new" element={<OwnerPropertyFormPage locale={locale} text={text} />} />
          <Route path="management/listings/:id/edit" element={<OwnerPropertyFormPage locale={locale} text={text} />} />
          <Route path="management/viewing-requests" element={<OwnerViewingRequestsPage text={text} />} />
          <Route path="management/brokerage" element={<BrokerageSettingsPage text={text} />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage text={text} />} />
      </Route>
    </Routes>
    </HomepageContentProvider>
    </BrokerageContactProvider>
  );
}
