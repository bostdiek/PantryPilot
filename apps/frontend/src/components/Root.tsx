import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { markSessionActivity } from '../api/session';
import { useAuthStore } from '../stores/useAuthStore';
import { restoreSessionRecovery } from '../utils/sessionRecovery';
import Navigation from './Navigation';
import { ToastContainer } from './ui/ToastContainer';

/**
 * Root layout component that wraps all routes
 * Contains the navigation and common layout elements
 */
const Root: React.FC = () => {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.token !== null);

  useEffect(() => {
    restoreSessionRecovery(location.pathname + location.search);
  }, [location.pathname, location.search]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const markActivity = (event: Event) => {
      if (event.isTrusted && document.visibilityState === 'visible') {
        void markSessionActivity();
      }
    };
    const events: Array<keyof DocumentEventMap> = [
      'pointerdown',
      'click',
      'keydown',
      'input',
      'change',
      'submit',
      'wheel',
      'touchstart',
    ];
    for (const event of events) {
      document.addEventListener(event, markActivity, true);
    }
    window.addEventListener('popstate', markActivity);
    window.addEventListener('focus', markActivity);

    return () => {
      for (const event of events) {
        document.removeEventListener(event, markActivity, true);
      }
      window.removeEventListener('popstate', markActivity);
      window.removeEventListener('focus', markActivity);
    };
  }, [isAuthenticated]);

  return (
    <>
      <Navigation />
      <Outlet />
      <ToastContainer />
    </>
  );
};

export default Root;
