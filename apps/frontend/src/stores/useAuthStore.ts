import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthState } from '../types/Auth';

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      login: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
    }),
    {
      name: 'auth-storage', // unique name for localStorage
      partialize: (state) => ({ token: state.token, user: state.user }), // only persist token and user
    }
  )
);
