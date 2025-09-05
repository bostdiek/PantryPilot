import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthState } from '../types/auth';

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hasHydrated: false, // hydration guard flag
      login: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
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
