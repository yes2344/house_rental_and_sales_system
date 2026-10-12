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
  const isAuthorizedBroker = account?.role === 'broker';
  const canViewProperties = isOwner || (isAuthorizedBroker && permissions.some((permission) => [
    'properties.view_all',
    'properties.moderate',
    'properties.edit_all',
    'properties.manage_assigned',
  ].includes(permission)));
  const canViewRequests = isOwner || (isAuthorizedBroker && permissions.some((permission) => permission.startsWith('viewings.')));
  const canManageSettings = isOwner || (isAuthorizedBroker && permissions.includes('settings.manage'));
  const canManageBrokers = isOwner;

  return (
    <div className="manager-shell">
      <nav className="manager-navigation" aria-label={text('managerNavigation')}>
        {canViewProperties && <NavLink to="/management/listings" end>{text('managerListings')}</NavLink>}
        {canViewRequests && <NavLink to="/management/viewing-requests">{text('managerViewingRequests')}</NavLink>}
        {canManageSettings && <NavLink to="/management/brokerage">{text('managerContactSettings')}</NavLink>}
        {canManageSettings && <NavLink to="/management/locations">{text('locationManagementTitle')}</NavLink>}
        {canManageBrokers && <a href="/admin-portal/delegated-accounts/">{text('managerBrokerAccounts')}</a>}
      </nav>
      <Outlet />
    </div>
  );
}
