import { Navigate, Outlet } from 'react-router-dom';

import { useAuth } from '../AuthContext';

export function RequireNonBroker() {
  const { account } = useAuth();

  if (account?.role === 'broker') {
    return <Navigate to="/management/listings" replace />;
  }

  return <Outlet />;
}
