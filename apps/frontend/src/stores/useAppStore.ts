import { create } from 'zustand';

interface AppState {
  currentPage: string;
  isMenuOpen: boolean;
  theme: 'light' | 'dark';

  setCurrentPage: (page: string) => void;
  toggleMenu: () => void;

  setTheme: (theme: 'light' | 'dark') => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentPage: 'home',
  isMenuOpen: false,
  theme: 'light',

  setCurrentPage: (page) => set({ currentPage: page }),
  toggleMenu: () => set((state) => ({ isMenuOpen: !state.isMenuOpen })),
  setTheme: (theme) => set({ theme }),
}));
