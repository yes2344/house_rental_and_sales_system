import {
  ArrowUpRight,
  Building2,
  CalendarDays,
  Heart,
  MapPinned,
  Search,
  Settings,
  Shield,
  UserRound,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

import { useAuth } from '../AuthContext';
import type { MessageKey } from '../i18n';

interface DashboardPageProps {
  text: (key: MessageKey) => string;
}

export function DashboardPage({ text }: DashboardPageProps) {
  const { account } = useAuth();
  if (!account) return null;

  const permissions = account.management_permissions;
  const isAdministrator = account.role === 'administrator';
  const isDjangoAdmin = account.is_django_admin;
  const isBroker = account.role === 'broker';
  const canManageListings = isBroker && permissions.some((permission) => permission.startsWith('properties.'));
  const canManageRequests = isBroker && permissions.some((permission) => permission.startsWith('viewings.'));
  const canManageSettings = isBroker && permissions.includes('settings.manage');
  const canManageBrokers = account.role === 'administrator' && permissions.includes('users.manage');

  const entries: {
    href: string;
    title: string;
    icon: ReactNode;
  }[] = [
    ...(isAdministrator
      ? (canManageBrokers && !isDjangoAdmin ? [
        { href: '/management/brokers', title: text('managerBrokerAccounts'), icon: <Users aria-hidden="true" /> },
      ] : [])
      : [
      { href: '/properties', title: text('explore'), icon: <Search aria-hidden="true" /> },
      { href: '/favorites', title: text('savedHomesTitle'), icon: <Heart aria-hidden="true" /> },
      { href: '/account', title: text('accountTitle'), icon: <UserRound aria-hidden="true" /> },
      ]),
  ];

  if (!isAdministrator && account.role !== 'broker') {
    entries.push({
      href: '/viewing-requests',
      title: text('yourViewingRequests'),
      icon: <CalendarDays aria-hidden="true" />,
    });
  }
  if (canManageListings) {
    entries.push({
      href: '/management/listings',
      title: text('managerListings'),
      icon: <Building2 aria-hidden="true" />,
    });
  }
  if (canManageRequests) {
    entries.push({
      href: '/management/viewing-requests',
      title: text('managerViewingRequests'),
      icon: <CalendarDays aria-hidden="true" />,
    });
  }
  if (canManageSettings) {
    entries.push({
      href: '/management/brokerage',
      title: text('managerContactSettings'),
      icon: <Settings aria-hidden="true" />,
    });
    entries.push({
      href: '/management/locations',
      title: text('locationManagementTitle'),
      icon: <MapPinned aria-hidden="true" />,
    });
  }
  if (canManageBrokers && !isAdministrator) {
    entries.push({
      href: '/management/brokers',
      title: text('managerBrokerAccounts'),
      icon: <Users aria-hidden="true" />,
    });
  }

  return (
    <main id="main-content" className="customer-page">
      <section className="customer-heading">
        <div className="container">
          <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text(isAdministrator ? 'adminDashboardTitle' : 'dashboardTitle')}</p>
          <h1>{text(isAdministrator ? 'adminDashboardTitle' : 'dashboardTitle')}</h1>
          <p>{text('accountWelcome')} <strong>{account.username}</strong></p>
          <p>{text(isAdministrator ? 'adminDashboardIntro' : 'dashboardIntro')}</p>
        </div>
      </section>
      <section className="container customer-content">
        <div className="role-dashboard-grid">
          {entries.map((entry) => (
            <Link className="role-dashboard-card" key={entry.href} to={entry.href}>
              <span className="role-dashboard-icon">{entry.icon}</span>
              <strong>{entry.title}</strong>
              <span className="role-dashboard-open">{text('dashboardOpenSection')}<ArrowUpRight size={15} aria-hidden="true" /></span>
            </Link>
          ))}
          {isDjangoAdmin && (
            <Link className="role-dashboard-card" to="/admin">
              <span className="role-dashboard-icon"><Shield aria-hidden="true" /></span>
              <strong>{text('openPlatformAdmin')}</strong>
              <span className="role-dashboard-open">{text('dashboardOpenSection')}<ArrowUpRight size={15} aria-hidden="true" /></span>
            </Link>
          )}
        </div>
      </section>
    </main>
  );
}
