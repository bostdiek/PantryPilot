import type { Meal, MealPlan } from '../../types/MealPlan';
import type { ApiResponse } from '../../types/api';
import { apiClient } from '../client';

// Get the current week's meal plan
export async function getWeeklyMealPlan(): Promise<ApiResponse<MealPlan>> {
  return apiClient.request<ApiResponse<MealPlan>>('/api/v1/mealplans/weekly', {
    method: 'GET',
  });
}

// Update the weekly meal plan (send the whole array)
export async function updateWeeklyMealPlan(
  mealPlan: MealPlan
): Promise<ApiResponse<MealPlan>> {
  return apiClient.request<ApiResponse<MealPlan>>('/api/v1/mealplans/weekly', {
    method: 'PUT',
    body: JSON.stringify(mealPlan),
  });
}

// Get a single day's meal (by date or dayOfWeek)
export async function getMealByDay(day: string): Promise<ApiResponse<Meal>> {
  // day can be '2025-08-21' or 'Monday', depending on backend
  return apiClient.request<ApiResponse<Meal>>(`/api/v1/meals/${day}`, {
    method: 'GET',
  });
}

// Update a single day's meal
export async function updateMealByDay(
  day: string,
  meal: Partial<Meal>
): Promise<ApiResponse<Meal>> {
  return apiClient.request<ApiResponse<Meal>>(`/api/v1/meals/${day}`, {
    method: 'PATCH',
    body: JSON.stringify(meal),
  });
}
