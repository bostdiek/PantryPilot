import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { AuthState } from '../types/auth';
import { captureSessionRecovery } from '../utils/sessionRecovery';
import { getSessionClaims, isSameSession } from '../utils/authSession';
import { logger } from '../lib/logger';
import {
  addToastIfNotExists,
  generateToastId,
} from '../components/ui/toast-utils';

let applyingExternalSessionChange = false;

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      hasHydrated: false, // hydration guard flag
      login: (token, user) => set({ token, user }),
      logout: (reason?: 'expired' | 'manual') => {
        if (reason === 'expired') {
          captureSessionRecovery(get().user?.id);
        }
        set({ token: null, user: null });

        // Show user-friendly message for token expiration (avoid duplicates)
        if (reason === 'expired') {
          addToastIfNotExists({
            id: generateToastId(),
            message: [
              'Your session could not continue. It may need confirmation',
              'or have reached its maximum duration. Sign in again; recoverable form',
              'and chat text are saved in this tab.',
            ].join(' '),
            type: 'info',
          });
        }
      },
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      getDisplayName: () => {
        const state = get();
        if (!state.user) return 'Guest';

        const { first_name, last_name, username } = state.user;

        // If we have first_name or last_name, construct display name
        if (first_name || last_name) {
          return [first_name, last_name].filter(Boolean).join(' ').trim();
        }

        // Fall back to username
        return username;
      },
    }),
    {
      name: 'auth', // persist middleware name for localStorage
      storage: createJSONStorage(() => ({
        getItem: (name) => localStorage.getItem(name),
        setItem: (name, value) => {
          if (!applyingExternalSessionChange) localStorage.setItem(name, value);
        },
        removeItem: (name) => localStorage.removeItem(name),
      })),
      partialize: (state) => ({ token: state.token, user: state.user }), // only persist token and user
      onRehydrateStorage: () => (state) => {
        // Set hasHydrated=true after rehydration finishes
        if (state) {
          state.hasHydrated = true;
        }
      },
    }
  )
);

/** Invalidate stale tabs without installing another account into their open forms. */
export function listenForSessionChanges(): () => void {
  const onStorage = (event: StorageEvent) => {
    if (event.key !== 'auth' && event.key !== null) return;
    const currentToken = useAuthStore.getState().token;
    if (!currentToken) return;

    let remoteToken: string | null = null;
    try {
      const persisted: unknown = event.newValue
        ? JSON.parse(event.newValue)
        : null;
      if (
        persisted &&
        typeof persisted === 'object' &&
        'state' in persisted &&
        persisted.state &&
        typeof persisted.state === 'object' &&
        'token' in persisted.state &&
        typeof persisted.state.token === 'string'
      ) {
        remoteToken = persisted.state.token;
      }
    } catch (error) {
      logger.warn(
        'Could not read authentication change from another tab',
        error
      );
    }
    if (isSameSession(currentToken, remoteToken)) {
      const currentDeadline = getSessionClaims(currentToken)?.session_exp;
      const remoteDeadline = getSessionClaims(remoteToken)?.session_exp;
      if (
        remoteDeadline &&
        (!currentDeadline || remoteDeadline > currentDeadline)
      ) {
        applyingExternalSessionChange = true;
        try {
          useAuthStore.getState().setToken(remoteToken);
        } finally {
          applyingExternalSessionChange = false;
        }
      }
      return;
    }

    applyingExternalSessionChange = true;
    try {
      useAuthStore.getState().logout('expired');
    } finally {
      applyingExternalSessionChange = false;
    }
  };
  window.addEventListener('storage', onStorage);
  return () => window.removeEventListener('storage', onStorage);
}

// Convenience selector hook for derived authentication boolean
export const useIsAuthenticated = () => useAuthStore((s) => s.token !== null);

// Convenience hook for display name
export const useDisplayName = () => useAuthStore((s) => s.getDisplayName());
