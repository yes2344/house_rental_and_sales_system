import { NavLink, Outlet } from 'react-router-dom';

import type { MessageKey } from '../i18n';

interface OwnerDashboardLayoutProps {
  text: (key: MessageKey) => string;
}

export function OwnerDashboardLayout({ text }: OwnerDashboardLayoutProps) {
  return (
    <div className="manager-shell">
      <nav className="manager-navigation" aria-label={text('managerNavigation')}>
        <NavLink to="/owner/listings" end>{text('managerListings')}</NavLink>
        <NavLink to="/owner/viewing-requests">{text('managerViewingRequests')}</NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
