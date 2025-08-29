import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useRecipeStore } from '../useRecipeStore';

// Mock API endpoints module
vi.mock('../../api/endpoints/recipes', () => ({
  getAllRecipes: vi.fn().mockResolvedValue([]),
  getRecipeById: vi.fn(),
  createRecipe: vi.fn(),
  updateRecipe: vi.fn(),
  deleteRecipe: vi.fn(),
}));

import {
  getRecipeById,
  createRecipe as apiCreateRecipe,
  getAllRecipes,
} from '../../api/endpoints/recipes';

const baseRecipe = {
  id: 'r1',
  title: 'Pizza',
  description: 'Delicious',
  ingredients: [{ name: 'Flour' }],
  instructions: ['Mix', 'Bake'],
  prep_time_minutes: 10,
  cook_time_minutes: 20,
  total_time_minutes: 30,
  serving_min: 2,
  difficulty: 'easy',
  category: 'dinner',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('useRecipeStore.duplicateRecipe', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // reset store
    const { getState, setState } = useRecipeStore as unknown as {
      getState: () => any;
      setState: (partial: any) => void;
    };
    setState({ ...getState(), recipes: [baseRecipe] });
  });

  it('prefers store recipe over API fetch when duplicating', async () => {
    vi.mocked(getRecipeById).mockResolvedValue(null as any);
    vi.mocked(apiCreateRecipe).mockResolvedValue({
      ...baseRecipe,
      id: 'r2',
      title: 'Pizza (Copy)',
    } as any);
    vi.mocked(getAllRecipes).mockResolvedValue([
      baseRecipe,
      { ...baseRecipe, id: 'r2', title: 'Pizza (Copy)' },
    ] as any);

    const { duplicateRecipe } = useRecipeStore.getState();
    const result = await duplicateRecipe('r1');

    expect(getRecipeById).not.toHaveBeenCalled(); // store had the recipe
    expect(apiCreateRecipe).toHaveBeenCalled();
    expect(result?.title).toBe('Pizza (Copy)');
  });
});
