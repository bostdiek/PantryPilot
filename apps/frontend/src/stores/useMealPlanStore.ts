import { create } from 'zustand';
import type { Recipe } from '../types/Recipe';

interface MealPlanDay {
  day: string;
  recipe: Recipe | null;
  notes?: string;
}

interface MealPlanWeek {
  startDate: Date;
  days: MealPlanDay[];
}

interface MealPlanState {
  currentWeek: MealPlanWeek | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchCurrentWeek: () => Promise<void>;
  assignRecipeToDay: (day: string, recipeId: string) => Promise<void>;
  generateGroceryList: () => Promise<string[]>;
}

// This is a mock implementation for now
export const useMealPlanStore = create<MealPlanState>((set) => ({
  currentWeek: null,
  isLoading: false,
  error: null,

  fetchCurrentWeek: async () => {
    set({ isLoading: true, error: null });
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // For now, return an empty meal plan
      set({
        currentWeek: {
          startDate: new Date(),
          days: [
            { day: 'Monday', recipe: null },
            { day: 'Tuesday', recipe: null },
            { day: 'Wednesday', recipe: null },
            { day: 'Thursday', recipe: null },
            { day: 'Friday', recipe: null },
            { day: 'Saturday', recipe: null },
            { day: 'Sunday', recipe: null },
          ],
        },
        isLoading: false,
      });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : 'Failed to fetch meal plan',
        isLoading: false,
      });
    }
  },

  assignRecipeToDay: async (day, recipeId) => {
    set({ isLoading: true, error: null });
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // This would update the meal plan with the recipe
      set((state) => {
        if (!state.currentWeek) return state;

        const updatedDays = state.currentWeek.days.map((d) =>
          d.day === day
            ? { ...d, recipe: { id: recipeId } as any } // This is a simplification
            : d
        );

        return {
          ...state,
          currentWeek: {
            ...state.currentWeek,
            days: updatedDays,
          },
          isLoading: false,
        };
      });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : 'Failed to assign recipe',
        isLoading: false,
      });
    }
  },

  generateGroceryList: async () => {
    set({ isLoading: true, error: null });
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Mock grocery list
      const groceryList = ['Eggs', 'Milk', 'Bread', 'Vegetables'];

      set({ isLoading: false });
      return groceryList;
    } catch (error) {
      set({
        error:
          error instanceof Error
            ? error.message
            : 'Failed to generate grocery list',
        isLoading: false,
      });
      return [];
    }
  },
}));
