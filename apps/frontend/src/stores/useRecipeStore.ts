import { create } from 'zustand';
import {
  createRecipe as apiCreateRecipe,
  deleteRecipe as apiDeleteRecipe,
  updateRecipe as apiUpdateRecipe,
  extractDuplicateInfo,
  getAllRecipes,
  getRecipeById,
  type DuplicateRecipeError,
} from '../api/endpoints/recipes';
import { logger } from '../lib/logger';
import type { AIDraftPayload } from '../types/AIDraft';
import type { ApiError } from '../types/api';
import type {
  Recipe,
  RecipeCategory,
  RecipeCreate,
  RecipeDifficulty,
  RecipeUpdate,
} from '../types/Recipe';

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

  // AI suggestion state for form prefilling
  formSuggestion: RecipeCreate | null;
  isAISuggestion: boolean;

  // Duplicate detection state
  duplicateInfo: DuplicateRecipeError | null;
  pendingRecipeData: RecipeCreate | null;

  // Actions
  fetchRecipes: () => Promise<void>;
  fetchRecipeById: (id: string) => Promise<Recipe | null>;
  addRecipe: (
    recipe: RecipeCreate,
    options?: { force?: boolean }
  ) => Promise<Recipe | null>;
  forceCreateRecipe: () => Promise<Recipe | null>;
  clearDuplicateState: () => void;
  updateRecipe: (
    id: string,
    updates: Partial<Recipe>
  ) => Promise<Recipe | null>;
  deleteRecipe: (id: string) => Promise<boolean>;
  duplicateRecipe: (id: string) => Promise<Recipe | null>;

  // Search, filter, and sort actions
  setFilters: (filters: Partial<RecipeFilters>) => void;
  setSortBy: (sortBy: RecipeSortOption) => void;
  setPage: (page: number) => void;
  clearFilters: () => void;
  applyFiltersAndSort: () => void;

  // AI suggestion actions
  setFormFromSuggestion: (payload: AIDraftPayload) => void;
  clearFormSuggestion: () => void;
}

// Helper functions for filtering and sorting
function filterRecipes(recipes: Recipe[], filters: RecipeFilters): Recipe[] {
  return recipes.filter((recipe) => {
    // Text search in title and ingredients
    if (filters.query) {
      const query = filters.query.toLowerCase();
      const titleMatch = recipe.title.toLowerCase().includes(query);
      const ingredientMatch = recipe.ingredients.some((ing) =>
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
    const totalTime =
      (recipe.prep_time_minutes ?? 0) + (recipe.cook_time_minutes ?? 0);
    if (totalTime < filters.cookTimeMin || totalTime > filters.cookTimeMax) {
      return false;
    }

    // Included ingredients filter
    if (filters.includedIngredients.length > 0) {
      const hasAllIncluded = filters.includedIngredients.every((required) =>
        recipe.ingredients.some((ing) =>
          ing.name.toLowerCase().includes(required.toLowerCase())
        )
      );
      if (!hasAllIncluded) return false;
    }

    // Excluded ingredients filter
    if (filters.excludedIngredients.length > 0) {
      const hasExcluded = filters.excludedIngredients.some((excluded) =>
        recipe.ingredients.some((ing) =>
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
      return sorted.sort(
        (a, b) =>
          (a.prep_time_minutes ?? 0) +
          (a.cook_time_minutes ?? 0) -
          ((b.prep_time_minutes ?? 0) + (b.cook_time_minutes ?? 0))
      );
    case 'cook-time-desc':
      return sorted.sort(
        (a, b) =>
          (b.prep_time_minutes ?? 0) +
          (b.cook_time_minutes ?? 0) -
          ((a.prep_time_minutes ?? 0) + (a.cook_time_minutes ?? 0))
      );
    case 'recently-added':
      return sorted.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
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
  formSuggestion: null,
  isAISuggestion: false,
  duplicateInfo: null,
  pendingRecipeData: null,

  fetchRecipes: async () => {
    set({ isLoading: true, error: null });
    try {
      const recipes = await getAllRecipes();

      logger.debug('API response from fetchRecipes:', recipes);

      set({
        recipes,
        isLoading: false,
      });

      // Apply filters after fetching
      get().applyFiltersAndSort();
    } catch (error) {
      logger.error('Error fetching recipes:', error);
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

      logger.debug('API response from fetchRecipeById:', recipe);

      // No need to update the full recipes list for a single recipe fetch
      set({ isLoading: false });

      return recipe;
    } catch (error) {
      logger.error('Error fetching recipe by ID:', error);
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

  addRecipe: async (recipe: RecipeCreate, options?: { force?: boolean }) => {
    set({ isLoading: true, error: null, duplicateInfo: null });
    try {
      const newRecipe = await apiCreateRecipe(recipe, options);

      logger.debug('API response from addRecipe:', newRecipe);

      // Fetch all recipes to ensure we have the complete list
      const allRecipes = await getAllRecipes();

      set({
        recipes: allRecipes,
        isLoading: false,
        pendingRecipeData: null,
      });

      // Apply filters after adding
      get().applyFiltersAndSort();

      return newRecipe;
    } catch (error) {
      logger.error('Error adding recipe:', error);

      // Check if this is a duplicate error (409 Conflict)
      const dupInfo = extractDuplicateInfo(error);
      if (dupInfo) {
        logger.debug('Duplicate recipe detected:', dupInfo);
        set({
          duplicateInfo: dupInfo,
          pendingRecipeData: recipe,
          isLoading: false,
          error: null, // Don't set error for duplicates - handled by modal
        });
        return null;
      }

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

  forceCreateRecipe: async () => {
    const pendingData = get().pendingRecipeData;
    if (!pendingData) {
      logger.warn('No pending recipe data to force create');
      return null;
    }

    // Call addRecipe with force=true
    return get().addRecipe(pendingData, { force: true });
  },

  clearDuplicateState: () => {
    set({
      duplicateInfo: null,
      pendingRecipeData: null,
    });
  },

  updateRecipe: async (id: string, recipe: RecipeUpdate) => {
    set({ isLoading: true, error: null });
    try {
      const updatedRecipe = await apiUpdateRecipe(id, recipe);

      logger.debug('API response from updateRecipe:', updatedRecipe);

      set((state) => ({
        recipes: state.recipes.map((r) => (r.id === id ? updatedRecipe : r)),
        isLoading: false,
      }));

      // Apply filters after updating
      get().applyFiltersAndSort();

      return updatedRecipe;
    } catch (error) {
      logger.error('Error updating recipe:', error);
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
      logger.error('Error deleting recipe:', error);
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

  duplicateRecipe: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      // Try to find the original recipe in the store first
      let originalRecipe = get().recipes.find((r) => r.id === id);
      if (!originalRecipe) {
        // If not found, fetch from API
        originalRecipe = await getRecipeById(id);
      }
      if (!originalRecipe) {
        throw new Error('Recipe not found');
      }

      // Create a new recipe with modified title and no ID
      const duplicateData: RecipeCreate = {
        title: `${originalRecipe.title} (Copy)`,
        description: originalRecipe.description,
        ingredients: originalRecipe.ingredients.map((ing) => ({
          name: ing.name,
          quantity_value: ing.quantity_value,
          quantity_unit: ing.quantity_unit,
          prep: ing.prep,
          is_optional: ing.is_optional,
        })),
        instructions: [...originalRecipe.instructions],
        prep_time_minutes: originalRecipe.prep_time_minutes,
        cook_time_minutes: originalRecipe.cook_time_minutes,
        serving_min: originalRecipe.serving_min,
        serving_max: originalRecipe.serving_max,
        difficulty: originalRecipe.difficulty,
        category: originalRecipe.category,
        ethnicity: originalRecipe.ethnicity,
        oven_temperature_f: originalRecipe.oven_temperature_f,
        user_notes: originalRecipe.user_notes,
        link_source: originalRecipe.link_source,
      };

      // Create the new recipe using the existing addRecipe logic
      const newRecipe = await apiCreateRecipe(duplicateData);

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
      logger.error('Error duplicating recipe:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as ApiError)?.message ||
            `Failed to duplicate recipe with ID: ${id}`;

      set({
        error: errorMessage,
        isLoading: false,
      });

      return null;
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

  // AI suggestion actions
  setFormFromSuggestion: (payload: AIDraftPayload) => {
    // The backend returns payload directly as AIGeneratedRecipe, not wrapped
    // Check for various payload formats:
    // 1. recipe_data field (AI extraction format)
    // 2. generated_recipe.recipe_data (nested format for backward compatibility)
    // 3. Direct recipe fields (suggest_recipe tool format - has title, ingredients, etc.)
    let recipeData = null as unknown as any;

    if ((payload as any).recipe_data) {
      // Direct format: payload has recipe_data field
      recipeData = (payload as any).recipe_data;
    } else if ((payload as any).generated_recipe?.recipe_data) {
      // Nested format (for backward compatibility)
      recipeData = (payload as any).generated_recipe.recipe_data;
    } else if ((payload as any).title && (payload as any).ingredients) {
      // suggest_recipe tool format: recipe fields are directly on payload
      recipeData = payload;
    }

    if (recipeData) {
      logger.debug('Setting form suggestion with recipe data:', recipeData);
      set({
        formSuggestion: recipeData,
        isAISuggestion: true,
      });
    } else {
      // If extraction failed, clear the suggestion
      logger.debug('No recipe data found in payload, clearing suggestion');
      set({
        formSuggestion: null,
        isAISuggestion: true, // Keep flag to show AI panel
      });
    }
  },

  clearFormSuggestion: () => {
    set({
      formSuggestion: null,
      isAISuggestion: false,
    });
  },
}));
