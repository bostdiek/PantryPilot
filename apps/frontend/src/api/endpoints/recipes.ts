import type { Recipe } from '../../types/Recipe';
import type { ApiResponse } from '../../types/api';
import { apiClient } from '../client';

// Get all recipes
export async function getAllRecipes(): Promise<ApiResponse<Recipe[]>> {
  return apiClient.request<ApiResponse<Recipe[]>>('/api/v1/recipes', {
    method: 'GET',
  });
}

// Get a recipe by ID
export async function getRecipeById(id: string): Promise<ApiResponse<Recipe>> {
  return apiClient.request<ApiResponse<Recipe>>(`/api/v1/recipes/${id}`, {
    method: 'GET',
  });
}

// Create a new recipe
export async function createRecipe(
  recipe: Partial<Recipe>
): Promise<ApiResponse<Recipe>> {
  return apiClient.request<ApiResponse<Recipe>>('/api/v1/recipes', {
    method: 'POST',
    body: JSON.stringify(recipe),
  });
}

// Update an existing recipe
export async function updateRecipe(
  id: string,
  updates: Partial<Recipe>
): Promise<ApiResponse<Recipe>> {
  return apiClient.request<ApiResponse<Recipe>>(`/api/v1/recipes/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

// Delete a recipe
export async function deleteRecipe(id: string): Promise<ApiResponse<void>> {
  return apiClient.request<ApiResponse<void>>(`/api/v1/recipes/${id}`, {
    method: 'DELETE',
  });
}
