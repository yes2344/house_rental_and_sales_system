import { NavLink, Outlet } from 'react-router-dom';

import { useAuth } from '../AuthContext';
import type { MessageKey } from '../i18n';

interface OwnerDashboardLayoutProps {
  text: (key: MessageKey) => string;
}

export function OwnerDashboardLayout({ text }: OwnerDashboardLayoutProps) {
  const { account } = useAuth();
  const permissions = account?.management_permissions ?? [];
  const isAuthorizedBroker = account?.role === 'broker';
  const canViewProperties = isAuthorizedBroker && permissions.some((permission) => [
      'properties.view_all',
      'properties.moderate',
      'properties.edit_all',
      'properties.manage_assigned',
    ].includes(permission));
  const canViewRequests = isAuthorizedBroker
    && permissions.some((permission) => permission.startsWith('viewings.'));
  const canManageSubcities = isAuthorizedBroker && permissions.includes('locations.manage_subcities');
  const canManageBrokers = account?.role === 'administrator' && permissions.includes('staff.manage');
  const canManageCities = account?.role === 'administrator' && permissions.includes('locations.manage_cities');
  const canManageBranding = account?.role === 'administrator' && permissions.includes('branding.manage');

  return (
    <div className="manager-shell">
      <nav className="manager-navigation" aria-label={text('managerNavigation')}>
        {canViewProperties && <NavLink to="/management/listings" end>{text('managerListings')}</NavLink>}
        {canViewRequests && <NavLink to="/management/viewing-requests">{text('managerViewingRequests')}</NavLink>}
        {(canManageSubcities || canManageCities) && <NavLink to="/management/locations">{text('locationManagementTitle')}</NavLink>}
        {canManageBrokers && <NavLink to="/management/brokers">{text('managerBrokerAccounts')}</NavLink>}
        {canManageBranding && <NavLink to="/management/branding">{text('siteBrandingTitle')}</NavLink>}
      </nav>
      <Outlet />
    </div>
  );
}
