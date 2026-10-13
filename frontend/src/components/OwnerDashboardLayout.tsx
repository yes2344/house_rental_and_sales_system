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
  const canViewRequests = isAuthorizedBroker && permissions.some((permission) => permission.startsWith('viewings.'));
  const canManageSettings = isAuthorizedBroker && permissions.includes('settings.manage');
  const canManageBrokers = account?.role === 'administrator' && permissions.includes('users.manage');

  return (
    <div className="manager-shell">
      <nav className="manager-navigation" aria-label={text('managerNavigation')}>
        {canViewProperties && <NavLink to="/management/listings" end>{text('managerListings')}</NavLink>}
        {canViewRequests && <NavLink to="/management/viewing-requests">{text('managerViewingRequests')}</NavLink>}
        {canManageSettings && <NavLink to="/management/brokerage">{text('managerContactSettings')}</NavLink>}
        {canManageSettings && <NavLink to="/management/locations">{text('locationManagementTitle')}</NavLink>}
        {canManageBrokers && <NavLink to="/management/brokers">{text('managerBrokerAccounts')}</NavLink>}
      </nav>
      <Outlet />
    </div>
  );
}
