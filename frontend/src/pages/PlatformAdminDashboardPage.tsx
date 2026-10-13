import {
  ArrowUpRight,
  Building2,
  CalendarDays,
  MapPinned,
  Settings,
  Users,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../AuthContext';
import type { MessageKey } from '../i18n';

interface PlatformAdminDashboardPageProps {
  text: (key: MessageKey) => string;
}

export function PlatformAdminDashboardPage({ text }: PlatformAdminDashboardPageProps) {
  const { account } = useAuth();
  if (!account?.is_django_admin) return null;

  const permissions = account.management_permissions;
  const tasks: { href: string; title: MessageKey; description: MessageKey; icon: ReactNode }[] = [
    ...(permissions.some((permission) => permission.startsWith('properties.')) ? [{
      href: '/management/listings',
      title: 'managerListings' as const,
      description: 'adminListingsHelp' as const,
      icon: <Building2 aria-hidden="true" />,
    }] : []),
    ...(permissions.some((permission) => permission.startsWith('viewings.')) ? [{
      href: '/management/viewing-requests',
      title: 'managerViewingRequests' as const,
      description: 'adminViewingRequestsHelp' as const,
      icon: <CalendarDays aria-hidden="true" />,
    }] : []),
    ...(permissions.includes('users.manage') ? [{
      href: '/management/brokers',
      title: 'managerBrokerAccounts' as const,
      description: 'adminBrokerAccountsHelp' as const,
      icon: <Users aria-hidden="true" />,
    }] : []),
    ...(permissions.includes('settings.manage') ? [{
      href: '/management/locations',
      title: 'locationManagementTitle' as const,
      description: 'adminLocationsHelp' as const,
      icon: <MapPinned aria-hidden="true" />,
    }, {
      href: '/management/brokerage',
      title: 'managerContactSettings' as const,
      description: 'adminBrokerageSettingsHelp' as const,
      icon: <Settings aria-hidden="true" />,
    }] : []),
  ];

  return (
    <main id="main-content" className="customer-page">
      <section className="customer-heading">
        <div className="container">
          <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text('adminDashboardTitle')}</p>
          <h1>{text('adminDashboardTitle')}</h1>
          <p>{text('accountWelcome')} <strong>{account.username}</strong></p>
          <p>{text('adminDashboardIntro')}</p>
        </div>
      </section>
      <section className="container customer-content">
        <div className="role-dashboard-grid">
          {tasks.map((task) => (
            <Link className="role-dashboard-card admin-workspace-card" key={task.href} to={task.href}>
              <span className="role-dashboard-icon">{task.icon}</span>
              <strong>{text(task.title)}</strong>
              <span className="admin-workspace-description">{text(task.description)}</span>
              <span className="role-dashboard-open">{text('dashboardOpenSection')}<ArrowUpRight size={15} aria-hidden="true" /></span>
            </Link>
          ))}
          {tasks.length === 0 && <p role="alert">{text('adminNoManagementTools')}</p>}
        </div>
      </section>
    </main>
  );
}
