import type {
  Recipe,
  RecipeCategory,
  RecipeDifficulty,
} from '../../types/Recipe';
import { apiClient } from '../client';

// Paginated search response type
export interface RecipeSearchResponse {
  items: Recipe[];
  limit: number;
  offset: number;
  total?: number | null;
}

/**
 * Similar recipe match returned by duplicate detection
 */
export interface SimilarRecipeInfo {
  id: string;
  name: string;
  similarity: number;
}

/**
 * Duplicate recipe error response from the API (409 Conflict)
 */
export interface DuplicateRecipeError {
  message: string;
  existing_recipe_id?: string | null;
  similar_recipes?: SimilarRecipeInfo[];
  hint: string;
}

/**
 * Options for creating a recipe
 */
export interface CreateRecipeOptions {
  /** If true, skip duplicate checks and create anyway */
  force?: boolean;
}

/**
 * Result type for createRecipe with duplicate handling
 */
export type CreateRecipeResult =
  | { success: true; recipe: Recipe }
  | { success: false; isDuplicate: true; duplicateInfo: DuplicateRecipeError }
  | { success: false; isDuplicate: false; error: Error };

/**
 * Check if an error response is a duplicate recipe error (409 Conflict)
 * and extract the duplicate info from the error response.
 */
export function isDuplicateRecipeError(
  error: unknown
): error is { status: number; response: { detail: DuplicateRecipeError } } {
  if (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    (error as { status: number }).status === 409
  ) {
    const response = (error as { response?: unknown }).response;
    // FastAPI returns { detail: { message, existing_recipe_id, similar_recipes, hint } }
    if (response && typeof response === 'object') {
      // Check if response has detail (standard FastAPI HTTPException format)
      if ('detail' in response) {
        const detail = (response as { detail: unknown }).detail;
        return (
          typeof detail === 'object' &&
          detail !== null &&
          'message' in detail &&
          'hint' in detail
        );
      }
      // Also check if the response itself is the detail object (edge case)
      if ('message' in response && 'hint' in response) {
        return true;
      }
    }
  }
  return false;
}

/**
 * Extract duplicate recipe info from a 409 error response.
 * Call this after isDuplicateRecipeError returns true.
 */
export function extractDuplicateInfo(
  error: unknown
): DuplicateRecipeError | null {
  if (!isDuplicateRecipeError(error)) {
    return null;
  }
  const response = (error as { response?: unknown }).response as Record<
    string,
    unknown
  >;
  // Standard FastAPI format
  if ('detail' in response && typeof response.detail === 'object') {
    return response.detail as DuplicateRecipeError;
  }
  // Edge case: response itself is the detail
  if ('message' in response && 'hint' in response) {
    return response as unknown as DuplicateRecipeError;
  }
  return null;
}

// Get recipes (first page) while staying compatible with existing store
export async function getAllRecipes(params?: {
  query?: string;
  difficulty?: RecipeDifficulty;
  max_total_time?: number;
  category?: RecipeCategory;
  limit?: number; // default 50 for near-full list UX
  offset?: number;
}): Promise<Recipe[]> {
  const p = params || {};
  const search = new URLSearchParams();
  if (p.query) search.set('query', p.query);
  if (p.difficulty) search.set('difficulty', p.difficulty);
  if (p.max_total_time != null)
    search.set('max_total_time', String(p.max_total_time));
  if (p.category) search.set('category', p.category);
  search.set('limit', String(p.limit ?? 50));
  search.set('offset', String(p.offset ?? 0));

  const resp = await apiClient.request<RecipeSearchResponse>(
    `/api/v1/recipes?${search.toString()}`,
    { method: 'GET' }
  );
  return resp.items;
}

// Full search with pagination metadata (for future UIs)
export async function searchRecipes(params: {
  query?: string;
  difficulty?: RecipeDifficulty;
  max_total_time?: number;
  category?: RecipeCategory;
  limit?: number;
  offset?: number;
}): Promise<RecipeSearchResponse> {
  const p = params || {};
  const search = new URLSearchParams();
  if (p.query) search.set('query', p.query);
  if (p.difficulty) search.set('difficulty', p.difficulty);
  if (p.max_total_time != null)
    search.set('max_total_time', String(p.max_total_time));
  if (p.category) search.set('category', p.category);
  search.set('limit', String(p.limit ?? 20));
  search.set('offset', String(p.offset ?? 0));

  return apiClient.request<RecipeSearchResponse>(
    `/api/v1/recipes?${search.toString()}`,
    { method: 'GET' }
  );
}

// Get a recipe by ID
export async function getRecipeById(id: string): Promise<Recipe> {
  // The backend returns a direct recipe object
  return apiClient.request<Recipe>(`/api/v1/recipes/${id}`, {
    method: 'GET',
  });
}

/**
 * Create a new recipe with optional duplicate handling.
 *
 * @param recipe - The recipe data to create
 * @param options - Options including force flag to skip duplicate checks
 * @returns The created recipe
 * @throws ApiErrorImpl with status 409 if duplicate detected and force=false
 */
export async function createRecipe(
  recipe: Partial<Recipe>,
  options?: CreateRecipeOptions
): Promise<Recipe> {
  const queryParams = options?.force ? '?force=true' : '';
  return apiClient.request<Recipe>(`/api/v1/recipes${queryParams}`, {
    method: 'POST',
    body: JSON.stringify(recipe),
  });
}

/**
 * Create a recipe with structured duplicate handling.
 * Returns a discriminated union result instead of throwing on duplicates.
 *
 * @param recipe - The recipe data to create
 * @param options - Options including force flag to skip duplicate checks
 * @returns CreateRecipeResult with success status and data or error info
 */
export async function createRecipeWithDuplicateHandling(
  recipe: Partial<Recipe>,
  options?: CreateRecipeOptions
): Promise<CreateRecipeResult> {
  try {
    const result = await createRecipe(recipe, options);
    return { success: true, recipe: result };
  } catch (error) {
    const duplicateInfo = extractDuplicateInfo(error);
    if (duplicateInfo) {
      return {
        success: false,
        isDuplicate: true,
        duplicateInfo,
      };
    }
    return {
      success: false,
      isDuplicate: false,
      error: error instanceof Error ? error : new Error(String(error)),
    };
  }
}

// Update an existing recipe
export async function updateRecipe(
  id: string,
  updates: Partial<Recipe>
): Promise<Recipe> {
  return apiClient.request<Recipe>(`/api/v1/recipes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

// Delete a recipe
export async function deleteRecipe(id: string): Promise<void> {
  return apiClient.request<void>(`/api/v1/recipes/${id}`, {
    method: 'DELETE',
  });
}
