import { Outlet } from 'react-router-dom';

import type { Locale, MessageKey } from '../i18n';
import { Footer } from './Footer';
import { Header } from './Header';

interface PageLayoutProps {
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  preferenceError: string;
  text: (key: MessageKey) => string;
}

export function PageLayout({ locale, onLocaleChange, preferenceError, text }: PageLayoutProps) {
  return (
    <div className="app-shell">
      <Header
        locale={locale}
        onLocaleChange={onLocaleChange}
        preferenceError={preferenceError}
        text={text}
      />
      <Outlet />
      <Footer text={text} />
    </div>
  );
}
