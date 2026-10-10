import { NavLink, Outlet } from 'react-router-dom';

import { useAuth } from '../AuthContext';
import type { MessageKey } from '../i18n';

interface OwnerDashboardLayoutProps {
  text: (key: MessageKey) => string;
}

export function OwnerDashboardLayout({ text }: OwnerDashboardLayoutProps) {
  const { account } = useAuth();
  const permissions = account?.management_permissions ?? [];
  const isOwner = Boolean(account?.is_platform_owner);
  const canViewProperties = isOwner || permissions.some((permission) => [
    'properties.view_all',
    'properties.moderate',
    'properties.edit_all',
    'properties.manage_assigned',
  ].includes(permission));
  const canViewRequests = isOwner || permissions.some((permission) => permission.startsWith('viewings.'));
  const canManageSettings = isOwner || permissions.includes('settings.manage');
  const canReviewAnnouncements = isOwner || permissions.includes('properties.moderate');

  return (
    <div className="manager-shell">
      <nav className="manager-navigation" aria-label={text('managerNavigation')}>
        {canViewProperties && <NavLink to="/management/listings" end>{text('managerListings')}</NavLink>}
        {canViewRequests && <NavLink to="/management/viewing-requests">{text('managerViewingRequests')}</NavLink>}
        {canReviewAnnouncements && <NavLink to="/management/owner-announcements">Owner announcements</NavLink>}
        {canManageSettings && <NavLink to="/management/brokerage">{text('managerContactSettings')}</NavLink>}
      </nav>
      <Outlet />
    </div>
  );
}
