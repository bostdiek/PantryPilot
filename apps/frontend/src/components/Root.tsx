import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { getSessionIdentity } from '../utils/authSession';
import { listenForSessionChanges, useAuthStore } from '../stores/useAuthStore';
import { restoreSessionRecovery } from '../utils/sessionRecovery';
import Navigation from './Navigation';
import { SessionExpiryPrompt } from './SessionExpiryPrompt';
import { ToastContainer } from './ui/ToastContainer';

/**
 * Root layout component that wraps all routes
 * Contains the navigation and common layout elements
 */
const Root: React.FC = () => {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.token !== null);
  const userId = useAuthStore((state) => state.user?.id);
  const sessionIdentity = useAuthStore(
    (state) => getSessionIdentity(state.token) ?? state.token
  );

  useEffect(() => listenForSessionChanges(), []);

  useEffect(() => {
    if (isAuthenticated) {
      return restoreSessionRecovery(
        location.pathname + location.search,
        userId,
        () => {
          const state = useAuthStore.getState();
          return (
            (getSessionIdentity(state.token) ?? state.token) ===
              sessionIdentity && state.user?.id === userId
          );
        }
      );
    }
  }, [
    location.pathname,
    location.search,
    isAuthenticated,
    userId,
    sessionIdentity,
  ]);

  return (
    <>
      <Navigation />
      <Outlet />
      <SessionExpiryPrompt key={sessionIdentity ?? 'signed-out'} />
      <ToastContainer />
    </>
  );
};

export default Root;
