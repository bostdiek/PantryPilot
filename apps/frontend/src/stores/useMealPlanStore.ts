import { create } from 'zustand';
import {
  createMealEntry,
  deleteMealEntry,
  getWeeklyMealPlan,
  markMealCooked,
  updateMealEntry,
} from '../api/endpoints/mealPlans';
import type {
  MealEntryIn,
  MealEntryPatch,
  WeeklyMealPlan,
} from '../types/MealPlan';
import { getErrorMessage } from '../utils/errors';

interface MealPlanState {
  currentWeek: WeeklyMealPlan | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadWeek: (start?: string) => Promise<void>;
  addEntry: (entry: MealEntryIn) => Promise<void>;
  updateEntry: (id: string, patch: MealEntryPatch) => Promise<void>;
  removeEntry: (id: string) => Promise<void>;
  markCooked: (id: string, cookedAt?: string) => Promise<void>;
}

export const useMealPlanStore = create<MealPlanState>((set) => ({
  currentWeek: null,
  isLoading: false,
  error: null,

  loadWeek: async (start) => {
    set({ isLoading: true, error: null });
    try {
      const data = await getWeeklyMealPlan(start);
      set({ currentWeek: data, isLoading: false });
    } catch (error) {
      set({
        error: getErrorMessage(error, 'Failed to load meal plan'),
        isLoading: false,
      });
    }
  },

  addEntry: async (entry) => {
    set({ isLoading: true, error: null });
    try {
      const created = await createMealEntry(entry);
      set((state) => {
        const week = state.currentWeek;
        if (!week) return { ...state, isLoading: false };
        const day = week.days.find((d) => d.date === created.plannedForDate);
        if (day) {
          day.entries = [...day.entries, created].sort(
            (a, b) => a.orderIndex - b.orderIndex
          );
        }
        return { ...state, currentWeek: { ...week }, isLoading: false };
      });
    } catch (error) {
      set({
        error: getErrorMessage(error, 'Failed to add entry'),
        isLoading: false,
      });
    }
  },

  updateEntry: async (id, patch) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await updateMealEntry(id, patch);
      set((state) => {
        const week = state.currentWeek;
        if (!week) return { ...state, isLoading: false };
        // Remove from old day if moved
        for (const d of week.days) {
          const idx = d.entries.findIndex((e) => e.id === id);
          if (idx !== -1) {
            d.entries.splice(idx, 1);
            break;
          }
        }
        // Insert into new day
        const newDay = week.days.find((d) => d.date === updated.plannedForDate);
        if (newDay) {
          newDay.entries = [...newDay.entries, updated].sort(
            (a, b) => a.orderIndex - b.orderIndex
          );
        }
        return { ...state, currentWeek: { ...week }, isLoading: false };
      });
    } catch (error) {
      set({
        error: getErrorMessage(error, 'Failed to update entry'),
        isLoading: false,
      });
    }
  },

  removeEntry: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await deleteMealEntry(id);
      set((state) => {
        const week = state.currentWeek;
        if (!week) return { ...state, isLoading: false };
        for (const d of week.days) {
          d.entries = d.entries.filter((e) => e.id !== id);
        }
        return { ...state, currentWeek: { ...week }, isLoading: false };
      });
    } catch (error) {
      set({
        error: getErrorMessage(error, 'Failed to remove entry'),
        isLoading: false,
      });
    }
  },

  markCooked: async (id, cookedAt) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await markMealCooked(id, cookedAt);
      set((state) => {
        const week = state.currentWeek;
        if (!week) return { ...state, isLoading: false };
        for (const d of week.days) {
          const idx = d.entries.findIndex((e) => e.id === id);
          if (idx !== -1) {
            d.entries[idx] = updated;
            break;
          }
        }
        return { ...state, currentWeek: { ...week }, isLoading: false };
      });
    } catch (error) {
      set({
        error: getErrorMessage(error, 'Failed to mark cooked'),
        isLoading: false,
      });
    }
  },
}));
