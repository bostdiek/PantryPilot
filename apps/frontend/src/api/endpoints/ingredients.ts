import type { Ingredient } from '../../types/Ingredients';
import type { ApiResponse } from '../../types/api';
import { apiClient } from '../client';

// Get all ingredients
export async function getAllIngredients(): Promise<ApiResponse<Ingredient[]>> {
  return apiClient.request<ApiResponse<Ingredient[]>>('/api/v1/ingredients', {
    method: 'GET',
  });
}

// Get an ingredient by ID
export async function getIngredientById(
  id: string
): Promise<ApiResponse<Ingredient>> {
  return apiClient.request<ApiResponse<Ingredient>>(
    `/api/v1/ingredients/${id}`,
    { method: 'GET' }
  );
}

// Create a new ingredient
export async function createIngredient(
  ingredient: Partial<Ingredient>
): Promise<ApiResponse<Ingredient>> {
  return apiClient.request<ApiResponse<Ingredient>>('/api/v1/ingredients', {
    method: 'POST',
    body: JSON.stringify(ingredient),
  });
}

// Update an existing ingredient
export async function updateIngredient(
  id: string,
  updates: Partial<Ingredient>
): Promise<ApiResponse<Ingredient>> {
  return apiClient.request<ApiResponse<Ingredient>>(
    `/api/v1/ingredients/${id}`,
    {
      method: 'PATCH',
      body: JSON.stringify(updates),
    }
  );
}

// Delete an ingredient
export async function deleteIngredient(id: string): Promise<ApiResponse<void>> {
  return apiClient.request<ApiResponse<void>>(`/api/v1/ingredients/${id}`, {
    method: 'DELETE',
  });
}
