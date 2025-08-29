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

// Create a new recipe
export async function createRecipe(recipe: Partial<Recipe>): Promise<Recipe> {
  return apiClient.request<Recipe>('/api/v1/recipes', {
    method: 'POST',
    body: JSON.stringify(recipe),
  });
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
