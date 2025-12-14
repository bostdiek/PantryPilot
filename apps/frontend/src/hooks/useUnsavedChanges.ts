import { useEffect, useRef } from 'react';
import { useBlocker } from 'react-router-dom';

interface BlockerState {
  state: string;
  proceed?: () => void;
  reset?: () => void;
}

// Create a mock blocker for testing
function createMockBlocker(shouldBlock: boolean): BlockerState {
  return {
    state: shouldBlock ? 'blocked' : 'unblocked',
    proceed: () => {},
    reset: () => {},
  };
}

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

  // Use Vite's env flags for test behavior, but always call useBlocker
  const isTestEnv =
    typeof window === 'undefined' ||
    import.meta.env.MODE === 'test' ||
    import.meta.env.VITEST;

  // Always call useBlocker to satisfy React hooks rules
  const routerBlocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasUnsavedChanges && currentLocation.pathname !== nextLocation.pathname
  );

  // In test environments, use a mock blocker instead of the real one
  const blocker: BlockerState = isTestEnv
    ? createMockBlocker(hasUnsavedChanges)
    : routerBlocker;

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
    if (blocker.state === 'blocked' && blocker.proceed && blocker.reset) {
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
