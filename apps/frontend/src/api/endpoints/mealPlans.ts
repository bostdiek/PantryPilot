import type {
  MealEntry,
  MealEntryIn,
  MealEntryPatch,
  WeeklyMealPlan,
} from '../../types/MealPlan';
import { apiClient } from '../client';

// Helpers to convert between backend (snake_case) and frontend (camelCase)
function toCamelEntry(e: any): MealEntry {
  return {
    id: e.id,
    plannedForDate: e.planned_for_date,
    mealType: e.meal_type,
    recipeId: e.recipe_id ?? undefined,
    isLeftover: e.is_leftover,
    isEatingOut: e.is_eating_out,
    notes: e.notes ?? undefined,
    orderIndex: e.order_index,
    wasCooked: e.was_cooked,
    cookedAt: e.cooked_at ?? undefined,
  } as MealEntry;
}

function toSnakeEntryIn(e: MealEntryIn): any {
  return {
    planned_for_date: e.plannedForDate,
    meal_type: e.mealType ?? 'dinner',
    recipe_id: e.recipeId,
    is_leftover: e.isLeftover ?? false,
    is_eating_out: e.isEatingOut ?? false,
    notes: e.notes,
    order_index: e.orderIndex,
  };
}

function toSnakeEntryPatch(p: MealEntryPatch): any {
  const out: Record<string, unknown> = {};
  if (p.plannedForDate !== undefined) out.planned_for_date = p.plannedForDate;
  if (p.mealType !== undefined) out.meal_type = p.mealType;
  if (p.recipeId !== undefined) out.recipe_id = p.recipeId;
  if (p.isLeftover !== undefined) out.is_leftover = p.isLeftover;
  if (p.isEatingOut !== undefined) out.is_eating_out = p.isEatingOut;
  if (p.notes !== undefined) out.notes = p.notes;
  if (p.orderIndex !== undefined) out.order_index = p.orderIndex;
  if (p.wasCooked !== undefined) out.was_cooked = p.wasCooked;
  if (p.cookedAt !== undefined) out.cooked_at = p.cookedAt;
  return out;
}

function toCamelWeekly(data: any): WeeklyMealPlan {
  return {
    weekStartDate: data.week_start_date,
    days: (data.days || []).map((d: any) => ({
      dayOfWeek: d.day_of_week,
      date: d.date,
      entries: (d.entries || []).map(toCamelEntry),
    })),
  };
}

// Get the weekly meal plan; optional start: YYYY-MM-DD (Sunday)
export async function getWeeklyMealPlan(
  start?: string
): Promise<WeeklyMealPlan> {
  const qs = start ? `?start=${encodeURIComponent(start)}` : '';
  const resp = await apiClient.request<any>(`/api/v1/mealplans/weekly${qs}`, {
    method: 'GET',
  });
  return toCamelWeekly(resp);
}

// Replace the weekly meal plan with a list of entries for that week
export async function replaceWeeklyMealPlan(
  entries: MealEntryIn[],
  start?: string
): Promise<WeeklyMealPlan> {
  const qs = start ? `?start=${encodeURIComponent(start)}` : '';
  const payload = entries.map(toSnakeEntryIn);
  const resp = await apiClient.request<any>(`/api/v1/mealplans/weekly${qs}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  return toCamelWeekly(resp);
}

// Create a new meal entry
export async function createMealEntry(
  payload: MealEntryIn
): Promise<MealEntry> {
  const snake = toSnakeEntryIn(payload);
  const resp = await apiClient.request<any>('/api/v1/meals', {
    method: 'POST',
    body: JSON.stringify(snake),
  });
  return toCamelEntry(resp);
}

// Update an existing meal entry
export async function updateMealEntry(
  id: string,
  patch: MealEntryPatch
): Promise<MealEntry> {
  const snake = toSnakeEntryPatch(patch);
  const resp = await apiClient.request<any>(`/api/v1/meals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(snake),
  });
  return toCamelEntry(resp);
}

// Delete a meal entry
export async function deleteMealEntry(id: string): Promise<{ success: true }> {
  return apiClient.request<{ success: true }>(`/api/v1/meals/${id}`, {
    method: 'DELETE',
  });
}

// Mark a meal entry as cooked
export async function markMealCooked(
  id: string,
  cookedAt?: string
): Promise<MealEntry> {
  const resp = await apiClient.request<any>(`/api/v1/meals/${id}/cooked`, {
    method: 'POST',
    body: JSON.stringify(cookedAt ? { cooked_at: cookedAt } : {}),
  });
  return toCamelEntry(resp);
}
