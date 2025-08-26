import { create } from 'zustand';
import type { Recipe } from '../types/Recipe';

interface RecipeState {
  recipes: Recipe[];
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchRecipes: () => Promise<void>;
  addRecipe: (
    recipe: Omit<Recipe, 'id' | 'createdAt' | 'updatedAt'>
  ) => Promise<void>;
}

// This is a mock implementation for now
export const useRecipeStore = create<RecipeState>((set) => ({
  recipes: [],
  isLoading: false,
  error: null,

  fetchRecipes: async () => {
    set({ isLoading: true, error: null });
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Mock data would go here
      set({
        recipes: [],
        isLoading: false,
      });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : 'Failed to fetch recipes',
        isLoading: false,
      });
    }
  },

  addRecipe: async (recipeData) => {
    set({ isLoading: true, error: null });
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      const newRecipe: Recipe = {
        ...recipeData,
        id: `recipe-${Date.now()}`,
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      set((state) => ({
        recipes: [...state.recipes, newRecipe],
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to add recipe',
        isLoading: false,
      });
    }
  },
}));
