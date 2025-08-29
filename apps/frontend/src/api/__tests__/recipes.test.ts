import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Recipe } from '../../types/Recipe';
import { apiClient } from '../client';
import {
  createRecipe,
  deleteRecipe,
  getAllRecipes,
  getRecipeById,
  updateRecipe,
} from '../endpoints/recipes';

// Mock the API client
vi.mock('../client', () => ({
  apiClient: {
    request: vi.fn(),
  },
}));

describe('Recipe API endpoints', () => {
  const mockRecipe: Recipe = {
    id: '1',
    title: 'Test Recipe',
    description: 'Test description',
    ingredients: [
      { name: 'Test Ingredient', quantity_value: 1, quantity_unit: 'cup' },
    ],
    instructions: ['Step 1', 'Step 2'],
    prep_time_minutes: 10,
    cook_time_minutes: 20,
    serving_min: 2,
    serving_max: 4,
    difficulty: 'easy',
    category: 'dinner',
    total_time_minutes: 30,
    created_at: new Date(),
    updated_at: new Date(),
  };

  const mockRecipes = [mockRecipe];

  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('getAllRecipes calls API with query params and unwraps items', async () => {
    (apiClient.request as any).mockResolvedValueOnce({
      items: mockRecipes,
      limit: 50,
      offset: 0,
      total: mockRecipes.length,
    });

    const result = await getAllRecipes();

    expect(apiClient.request).toHaveBeenCalledWith(
      expect.stringMatching(/^\/api\/v1\/recipes(\?|$)/),
      {
        method: 'GET',
      }
    );
    expect(result).toEqual(mockRecipes);
  });

  it('getRecipeById calls API with correct endpoint and ID', async () => {
    (apiClient.request as any).mockResolvedValueOnce(mockRecipe);

    const result = await getRecipeById('1');

    expect(apiClient.request).toHaveBeenCalledWith('/api/v1/recipes/1', {
      method: 'GET',
    });
    expect(result).toEqual(mockRecipe);
  });

  it('createRecipe calls API with correct endpoint and data', async () => {
    const newRecipe = {
      title: 'New Recipe',
      ingredients: [{ name: 'New Ingredient' }],
      instructions: ['Step 1'],
      prep_time_minutes: 5,
      cook_time_minutes: 15,
      serving_min: 2,
      difficulty: 'easy' as const,
      category: 'lunch' as const,
    };

    (apiClient.request as any).mockResolvedValueOnce({
      ...newRecipe,
      id: '2',
      total_time_minutes: 20,
      created_at: new Date(),
      updated_at: new Date(),
    });

    const result = await createRecipe(newRecipe);

    expect(apiClient.request).toHaveBeenCalledWith('/api/v1/recipes', {
      method: 'POST',
      body: JSON.stringify(newRecipe),
    });
    expect(result).toHaveProperty('id');
    expect(result.title).toBe(newRecipe.title);
  });

  it('updateRecipe calls API with correct endpoint, ID and data', async () => {
    const updates = {
      title: 'Updated Recipe',
    };

    const updatedRecipe = {
      ...mockRecipe,
      ...updates,
    };

    (apiClient.request as any).mockResolvedValueOnce(updatedRecipe);

    const result = await updateRecipe('1', updates);

    expect(apiClient.request).toHaveBeenCalledWith('/api/v1/recipes/1', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
    expect(result.title).toBe(updates.title);
  });

  it('deleteRecipe calls API with correct endpoint and ID', async () => {
    (apiClient.request as any).mockResolvedValueOnce(undefined);

    await deleteRecipe('1');

    expect(apiClient.request).toHaveBeenCalledWith('/api/v1/recipes/1', {
      method: 'DELETE',
    });
  });

  it('handles API errors properly', async () => {
    const errorMessage = 'API Error';
    (apiClient.request as any).mockRejectedValueOnce(new Error(errorMessage));

    await expect(getAllRecipes()).rejects.toThrow(errorMessage);
  });
});
