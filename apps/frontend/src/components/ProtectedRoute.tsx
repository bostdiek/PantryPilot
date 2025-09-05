import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore, useIsAuthenticated } from '../stores/useAuthStore';

const ProtectedRoute: React.FC = () => {
  const { hasHydrated } = useAuthStore();
  const isAuthenticated = useIsAuthenticated();
  const location = useLocation();

  // If not hydrated yet, render nothing or a skeleton
  if (!hasHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  // If not authenticated, navigate to login with current location as query parameter
  if (!isAuthenticated) {
    const loginUrl = `/login?next=${encodeURIComponent(location.pathname + location.search)}`;
    return <Navigate to={loginUrl} replace />;
  }

  // If authenticated, render the protected route content
  return <Outlet />;
};

export default ProtectedRoute;
