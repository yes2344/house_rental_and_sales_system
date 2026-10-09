import { Outlet } from 'react-router-dom';

import type { Locale, MessageKey } from '../i18n';
import { Footer } from './Footer';
import { Header } from './Header';

interface PageLayoutProps {
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  text: (key: MessageKey) => string;
}

export function PageLayout({ locale, onLocaleChange, text }: PageLayoutProps) {
  return (
    <div className="app-shell">
      <Header locale={locale} onLocaleChange={onLocaleChange} text={text} />
      <Outlet />
      <Footer text={text} />
    </div>
  );
}
