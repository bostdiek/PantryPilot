import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  UserPreferences,
  UserPreferencesStore,
  UserPreferencesResponse,
} from '../types/UserPreferences';
import {
  defaultUserPreferences,
  toFrontendPreferences,
} from '../types/UserPreferences';

export const useUserPreferencesStore = create<UserPreferencesStore>()(
  persist(
    (set, _get) => ({
      preferences: defaultUserPreferences,
      isLoaded: false,

      updatePreferences: (newPreferences: Partial<UserPreferences>) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            ...newPreferences,
          },
        }));
      },

      resetPreferences: () => {
        set({
          preferences: defaultUserPreferences,
        });
      },

      loadPreferences: () => {
        // Mark as loaded after hydration
        set({ isLoaded: true });
      },

      syncWithBackend: (backendPrefs: UserPreferencesResponse) => {
        const frontendPrefs = toFrontendPreferences(backendPrefs);
        set({
          preferences: frontendPrefs,
          isLoaded: true,
        });
      },
    }),
    {
      name: 'user-preferences', // localStorage key
      partialize: (state) => ({
        preferences: state.preferences,
      }), // Only persist preferences, not loading state
      onRehydrateStorage: () => (state) => {
        // Set isLoaded=true after rehydration finishes
        if (state) {
          state.isLoaded = true;
        }
      },
    }
  )
);

// Convenience hooks for specific preference values
export const useThemePreference = () =>
  useUserPreferencesStore((state) => state.preferences.theme);

export const useFamilySize = () =>
  useUserPreferencesStore((state) => state.preferences.familySize);

export const useDefaultServings = () =>
  useUserPreferencesStore((state) => state.preferences.defaultServings);

export const useAllergies = () =>
  useUserPreferencesStore((state) => state.preferences.allergies);

export const useDietaryRestrictions = () =>
  useUserPreferencesStore((state) => state.preferences.dietaryRestrictions);
