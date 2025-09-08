import React, { useEffect } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore, useIsAuthenticated } from '../stores/useAuthStore';
import { userProfileApi } from '../api/endpoints/userProfile';
import type { AuthUser } from '../types/auth';

const ProtectedRoute: React.FC = () => {
  const { hasHydrated, token, user, setUser, logout } = useAuthStore();
  const isAuthenticated = useIsAuthenticated();
  const location = useLocation();

  // If we have a token but no user, fetch user profile
  useEffect(() => {
    const fetchUserProfile = async () => {
      if (hasHydrated && token && !user) {
        try {
          const profile = await userProfileApi.getProfile();

          // Convert UserProfileResponse to AuthUser format
          const authUser: AuthUser = {
            id: profile.id,
            username: profile.username,
            email: profile.email,
            first_name: profile.first_name,
            last_name: profile.last_name,
          };

          setUser(authUser);
        } catch (error) {
          console.error('Failed to fetch user profile:', error);
          // If profile fetch fails, the token might be invalid
          // Clear the auth state to force re-login
          logout();
        }
      }
    };

    fetchUserProfile();
  }, [hasHydrated, token, user, setUser, logout]);

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
