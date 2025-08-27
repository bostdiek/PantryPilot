import type { Recipe } from '../../types/Recipe';
import { apiClient } from '../client';

// Get all recipes
export async function getAllRecipes(): Promise<Recipe[]> {
  // The backend returns a direct array of recipes
  return apiClient.request<Recipe[]>('/api/v1/recipes', {
    method: 'GET',
  });
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
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

// Delete a recipe
export async function deleteRecipe(id: string): Promise<void> {
  return apiClient.request<void>(`/api/v1/recipes/${id}`, {
    method: 'DELETE',
  });
}
