import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthState } from '../types/auth';
import { addToastIfNotExists, generateToastId } from '../components/ui/toast-utils';

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      hasHydrated: false, // hydration guard flag
      login: (token, user) => set({ token, user }),
      logout: (reason?: 'expired' | 'manual') => {
        set({ token: null, user: null });
        
        // Show user-friendly message for token expiration (avoid duplicates)
        if (reason === 'expired') {
          addToastIfNotExists({
            id: generateToastId(),
            message: 'Your session has expired. Please log in again.',
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

// Convenience selector hook for derived authentication boolean
export const useIsAuthenticated = () => useAuthStore((s) => s.token !== null);

// Convenience hook for display name
export const useDisplayName = () => useAuthStore((s) => s.getDisplayName());
