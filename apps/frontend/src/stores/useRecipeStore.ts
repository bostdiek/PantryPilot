import { create } from 'zustand';
import {
  createRecipe as apiCreateRecipe,
  deleteRecipe as apiDeleteRecipe,
  updateRecipe as apiUpdateRecipe,
  getAllRecipes,
  getRecipeById,
} from '../api/endpoints/recipes';
import type { ApiError } from '../types/api';
import type { Recipe, RecipeCreate, RecipeUpdate, RecipeCategory, RecipeDifficulty } from '../types/Recipe';

// Sort options for recipes
export type RecipeSortOption = 
  | 'relevance' 
  | 'title-asc' 
  | 'title-desc'
  | 'cook-time-asc' 
  | 'cook-time-desc'
  | 'recently-added';

// Filter state for recipes
export interface RecipeFilters {
  query: string;
  categories: RecipeCategory[];
  difficulties: RecipeDifficulty[];
  cookTimeMin: number;
  cookTimeMax: number;
  includedIngredients: string[];
  excludedIngredients: string[];
}

// Pagination state
export interface RecipePagination {
  page: number;
  pageSize: number;
  total: number;
}

interface RecipeState {
  // Data
  recipes: Recipe[];
  filteredRecipes: Recipe[];
  isLoading: boolean;
  error: string | null;

  // Search and filtering state
  filters: RecipeFilters;
  sortBy: RecipeSortOption;
  pagination: RecipePagination;

  // Actions
  fetchRecipes: () => Promise<void>;
  fetchRecipeById: (id: string) => Promise<Recipe | null>;
  addRecipe: (recipe: RecipeCreate) => Promise<Recipe | null>;
  updateRecipe: (
    id: string,
    updates: Partial<Recipe>
  ) => Promise<Recipe | null>;
  deleteRecipe: (id: string) => Promise<boolean>;

  // Search, filter, and sort actions
  setFilters: (filters: Partial<RecipeFilters>) => void;
  setSortBy: (sortBy: RecipeSortOption) => void;
  setPage: (page: number) => void;
  clearFilters: () => void;
  applyFiltersAndSort: () => void;
}

// Helper functions for filtering and sorting
function filterRecipes(recipes: Recipe[], filters: RecipeFilters): Recipe[] {
  return recipes.filter(recipe => {
    // Text search in title and ingredients
    if (filters.query) {
      const query = filters.query.toLowerCase();
      const titleMatch = recipe.title.toLowerCase().includes(query);
      const ingredientMatch = recipe.ingredients.some(ing => 
        ing.name.toLowerCase().includes(query)
      );
      if (!titleMatch && !ingredientMatch) return false;
    }

    // Category filter
    if (filters.categories.length > 0) {
      if (!filters.categories.includes(recipe.category)) return false;
    }

    // Difficulty filter
    if (filters.difficulties.length > 0) {
      if (!filters.difficulties.includes(recipe.difficulty)) return false;
    }

    // Cook time range filter
    const totalTime = recipe.prep_time_minutes + recipe.cook_time_minutes;
    if (totalTime < filters.cookTimeMin || totalTime > filters.cookTimeMax) {
      return false;
    }

    // Included ingredients filter
    if (filters.includedIngredients.length > 0) {
      const hasAllIncluded = filters.includedIngredients.every(required => 
        recipe.ingredients.some(ing => 
          ing.name.toLowerCase().includes(required.toLowerCase())
        )
      );
      if (!hasAllIncluded) return false;
    }

    // Excluded ingredients filter
    if (filters.excludedIngredients.length > 0) {
      const hasExcluded = filters.excludedIngredients.some(excluded => 
        recipe.ingredients.some(ing => 
          ing.name.toLowerCase().includes(excluded.toLowerCase())
        )
      );
      if (hasExcluded) return false;
    }

    return true;
  });
}

function sortRecipes(recipes: Recipe[], sortBy: RecipeSortOption): Recipe[] {
  const sorted = [...recipes];
  
  switch (sortBy) {
    case 'title-asc':
      return sorted.sort((a, b) => a.title.localeCompare(b.title));
    case 'title-desc':
      return sorted.sort((a, b) => b.title.localeCompare(a.title));
    case 'cook-time-asc':
      return sorted.sort((a, b) => 
        (a.prep_time_minutes + a.cook_time_minutes) - (b.prep_time_minutes + b.cook_time_minutes)
      );
    case 'cook-time-desc':
      return sorted.sort((a, b) => 
        (b.prep_time_minutes + b.cook_time_minutes) - (a.prep_time_minutes + a.cook_time_minutes)
      );
    case 'recently-added':
      return sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    case 'relevance':
    default:
      // For relevance, keep original order (could be enhanced with scoring later)
      return sorted;
  }
}

// Default filter state
const defaultFilters: RecipeFilters = {
  query: '',
  categories: [],
  difficulties: [],
  cookTimeMin: 0,
  cookTimeMax: 240, // 4 hours max
  includedIngredients: [],
  excludedIngredients: [],
};

const defaultPagination: RecipePagination = {
  page: 1,
  pageSize: 24,
  total: 0,
};

export const useRecipeStore = create<RecipeState>((set, get) => ({
  recipes: [],
  filteredRecipes: [],
  isLoading: false,
  error: null,
  filters: defaultFilters,
  sortBy: 'relevance',
  pagination: defaultPagination,

  fetchRecipes: async () => {
    set({ isLoading: true, error: null });
    try {
      const recipes = await getAllRecipes();

      console.log('API response from fetchRecipes:', recipes);

      set({
        recipes,
        isLoading: false,
      });

      // Apply filters after fetching
      get().applyFiltersAndSort();
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

      // Apply filters after adding
      get().applyFiltersAndSort();

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

      // Apply filters after updating
      get().applyFiltersAndSort();

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

      // Apply filters after deleting
      get().applyFiltersAndSort();

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

  // Search, filter, and sort actions
  setFilters: (newFilters: Partial<RecipeFilters>) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
      pagination: { ...state.pagination, page: 1 }, // Reset to first page
    }));
    get().applyFiltersAndSort();
  },

  setSortBy: (sortBy: RecipeSortOption) => {
    set({ sortBy });
    get().applyFiltersAndSort();
  },

  setPage: (page: number) => {
    set((state) => ({
      pagination: { ...state.pagination, page },
    }));
  },

  clearFilters: () => {
    set({
      filters: defaultFilters,
      sortBy: 'relevance',
      pagination: { ...defaultPagination },
    });
    get().applyFiltersAndSort();
  },

  applyFiltersAndSort: () => {
    const state = get();
    const filtered = filterRecipes(state.recipes, state.filters);
    const sorted = sortRecipes(filtered, state.sortBy);
    
    set({
      filteredRecipes: sorted,
      pagination: {
        ...state.pagination,
        total: sorted.length,
      },
    });
  },
}));
