import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthState } from '../types/Auth';

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false, // will be derived from token !== null
      hasHydrated: false, // hydration guard flag
      login: (token, user) => set({ token, user, isAuthenticated: token !== null }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
      setToken: (token) => set({ token, isAuthenticated: token !== null }),
      setUser: (user) => set({ user }),
    }),
    {
      name: 'auth', // persist middleware name for localStorage
      partialize: (state) => ({ token: state.token, user: state.user }), // only persist token and user
      onRehydrateStorage: () => (state) => {
        // Set hasHydrated=true after rehydration finishes and derive isAuthenticated
        if (state) {
          state.hasHydrated = true;
          state.isAuthenticated = state.token !== null;
        }
      },
    }
  )
);
