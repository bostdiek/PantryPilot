import { apiClient } from '../client';

// Types for grocery list API
export interface GroceryListRequest {
  start_date: string; // ISO date string
  end_date: string; // ISO date string
}

export interface GroceryListIngredient {
  id: string;
  name: string;
  quantity_value: number;
  quantity_unit: string;
  recipes: string[];
}

export interface GroceryListResponse {
  start_date: string;
  end_date: string;
  ingredients: GroceryListIngredient[];
  total_meals: number;
}

export const groceryListsApi = {
  async generateGroceryList(
    request: GroceryListRequest
  ): Promise<GroceryListResponse> {
    return apiClient.request<GroceryListResponse>('/api/v1/grocery-lists', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
};