import { Outlet } from 'react-router-dom';

import { useAuth } from '../AuthContext';
import type { MessageKey } from '../i18n';

interface RequireDjangoAdminProps {
  text: (key: MessageKey) => string;
}

export function RequireDjangoAdmin({ text }: RequireDjangoAdminProps) {
  const { account } = useAuth();

  if (account?.is_django_admin) return <Outlet />;

  return (
    <main className="account-state-page" id="main-content">
      <section className="account-state-card" role="alert">
        <h1>{text('managerAccessTitle')}</h1>
        <p>{text('managerAccessBody')}</p>
      </section>
    </main>
  );
}
