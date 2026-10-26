import { Navigate } from 'react-router-dom';

export function DjangoAdminLoginPage() {
  return <Navigate to="/login" replace state={{ from: '/admin' }} />;
}