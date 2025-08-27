import { create } from 'zustand';
import {
  createRecipe as apiCreateRecipe,
  deleteRecipe as apiDeleteRecipe,
  updateRecipe as apiUpdateRecipe,
  getAllRecipes,
  getRecipeById,
} from '../api/endpoints/recipes';
import type { ApiError } from '../types/api';
import type { Recipe, RecipeCreate, RecipeUpdate } from '../types/Recipe';

interface RecipeState {
  recipes: Recipe[];
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchRecipes: () => Promise<void>;
  fetchRecipeById: (id: string) => Promise<Recipe | null>;
  addRecipe: (recipe: RecipeCreate) => Promise<Recipe | null>;
  updateRecipe: (
    id: string,
    updates: Partial<Recipe>
  ) => Promise<Recipe | null>;
  deleteRecipe: (id: string) => Promise<boolean>;
}

export const useRecipeStore = create<RecipeState>((set) => ({
  recipes: [],
  isLoading: false,
  error: null,

  fetchRecipes: async () => {
    set({ isLoading: true, error: null });
    try {
      const recipes = await getAllRecipes();

      console.log('API response from fetchRecipes:', recipes);

      set({
        recipes,
        isLoading: false,
      });
    } catch (error) {
      console.error('Error fetching recipes:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as ApiError)?.message || 'Failed to fetch recipes';

      // Set an error but don't clear existing recipes if we already have them
      set((state) => ({
        error: errorMessage,
        isLoading: false,
        // Keep existing recipes if we have them (don't replace with empty array)
        recipes: state.recipes.length > 0 ? state.recipes : [],
      }));
    }
  },

  fetchRecipeById: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const recipe = await getRecipeById(id);

      console.log('API response from fetchRecipeById:', recipe);

      // No need to update the full recipes list for a single recipe fetch
      set({ isLoading: false });

      return recipe;
    } catch (error) {
      console.error('Error fetching recipe by ID:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as ApiError)?.message ||
            `Failed to fetch recipe with ID: ${id}`;

      set({
        error: errorMessage,
        isLoading: false,
      });

      return null;
    }
  },

  addRecipe: async (recipe: RecipeCreate) => {
    set({ isLoading: true, error: null });
    try {
      const newRecipe = await apiCreateRecipe(recipe);

      console.log('API response from addRecipe:', newRecipe);

      // Fetch all recipes to ensure we have the complete list
      const allRecipes = await getAllRecipes();

      set({
        recipes: allRecipes,
        isLoading: false,
      });

      return newRecipe;
    } catch (error) {
      console.error('Error adding recipe:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as ApiError)?.message || 'Failed to add recipe';

      set({
        error: errorMessage,
        isLoading: false,
      });

      return null;
    }
  },

  updateRecipe: async (id: string, recipe: RecipeUpdate) => {
    set({ isLoading: true, error: null });
    try {
      const updatedRecipe = await apiUpdateRecipe(id, recipe);

      console.log('API response from updateRecipe:', updatedRecipe);

      set((state) => ({
        recipes: state.recipes.map((r) => (r.id === id ? updatedRecipe : r)),
        isLoading: false,
      }));

      return updatedRecipe;
    } catch (error) {
      console.error('Error updating recipe:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as ApiError)?.message ||
            `Failed to update recipe with ID: ${id}`;

      set({
        error: errorMessage,
        isLoading: false,
      });

      return null;
    }
  },

  deleteRecipe: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await apiDeleteRecipe(id);

      set((state) => ({
        recipes: state.recipes.filter((recipe) => recipe.id !== id),
        isLoading: false,
      }));

      return true;
    } catch (error) {
      console.error('Error deleting recipe:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as ApiError)?.message ||
            `Failed to delete recipe with ID: ${id}`;

      set({
        error: errorMessage,
        isLoading: false,
      });

      return false;
    }
  },
}));
