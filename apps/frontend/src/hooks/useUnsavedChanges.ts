import { useEffect, useRef } from 'react';
import { useBlocker } from 'react-router-dom';

/**
 * Hook for blocking navigation when there are unsaved changes
 * @param hasUnsavedChanges - Whether there are unsaved changes
 * @param message - Custom message to show in the confirmation dialog
 */
export function useUnsavedChanges(
  hasUnsavedChanges: boolean,
  message = 'You have unsaved changes. Are you sure you want to leave?'
) {
  const hasUnsavedChangesRef = useRef(hasUnsavedChanges);
  
  // Update ref when hasUnsavedChanges changes
  hasUnsavedChangesRef.current = hasUnsavedChanges;

  // Try to use blocker, but handle cases where it's not available (like in tests)
  let blocker;
  try {
    blocker = useBlocker(
      ({ currentLocation, nextLocation }) =>
        hasUnsavedChangesRef.current && currentLocation.pathname !== nextLocation.pathname
    );
  } catch (error) {
    // useBlocker not available (e.g., in tests with MemoryRouter)
    blocker = { state: 'unblocked' };
  }

  // Handle browser refresh/close
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (hasUnsavedChangesRef.current) {
        event.preventDefault();
        event.returnValue = message;
        return message;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [message]);

  // Show confirmation dialog for router navigation
  useEffect(() => {
    if (blocker && blocker.state === 'blocked') {
      const shouldProceed = window.confirm(message);
      if (shouldProceed) {
        blocker.proceed();
      } else {
        blocker.reset();
      }
    }
  }, [blocker, message]);

  return blocker;
}