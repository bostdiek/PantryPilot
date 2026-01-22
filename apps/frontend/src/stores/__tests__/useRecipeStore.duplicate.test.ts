import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRecipeStore } from '../useRecipeStore';

// Mock API endpoints module
vi.mock('../../api/endpoints/recipes', () => ({
  getAllRecipes: vi.fn().mockResolvedValue([]),
  getRecipeById: vi.fn(),
  createRecipe: vi.fn(),
  updateRecipe: vi.fn(),
  deleteRecipe: vi.fn(),
  extractDuplicateInfo: vi.fn(),
}));

import {
  createRecipe as apiCreateRecipe,
  extractDuplicateInfo,
  getAllRecipes,
  getRecipeById,
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

describe('useRecipeStore duplicate detection state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store to initial state
    const { setState } = useRecipeStore as unknown as {
      setState: (partial: any) => void;
    };
    setState({
      recipes: [],
      duplicateInfo: null,
      pendingRecipeData: null,
      isLoading: false,
      error: null,
    });
  });

  describe('clearDuplicateState', () => {
    it('clears duplicateInfo and pendingRecipeData', () => {
      const { setState, getState } = useRecipeStore as unknown as {
        setState: (partial: any) => void;
        getState: () => any;
      };

      // Set some duplicate state
      setState({
        duplicateInfo: {
          message: 'Duplicate found',
          existing_recipe_id: 'abc-123',
          hint: 'Force create',
        },
        pendingRecipeData: { title: 'Test Recipe' },
      });

      // Verify state was set
      expect(getState().duplicateInfo).not.toBeNull();
      expect(getState().pendingRecipeData).not.toBeNull();

      // Clear state
      const { clearDuplicateState } = getState();
      clearDuplicateState();

      // Verify state was cleared
      expect(getState().duplicateInfo).toBeNull();
      expect(getState().pendingRecipeData).toBeNull();
    });
  });

  describe('addRecipe with duplicate detection', () => {
    it('stores duplicate info on 409 error', async () => {
      const duplicateError = {
        status: 409,
        response: {
          detail: {
            message: 'Recipe already exists',
            existing_recipe_id: 'existing-123',
            similar_recipes: [],
            hint: 'Use force=true',
          },
        },
      };

      vi.mocked(apiCreateRecipe).mockRejectedValue(duplicateError);
      vi.mocked(extractDuplicateInfo).mockReturnValue({
        message: 'Recipe already exists',
        existing_recipe_id: 'existing-123',
        similar_recipes: [],
        hint: 'Use force=true',
      });

      const { addRecipe } = useRecipeStore.getState();
      const recipeData = {
        title: 'New Recipe',
        description: 'Test',
        ingredients: [],
        instructions: [],
        prep_time_minutes: 10,
        cook_time_minutes: 20,
        total_time_minutes: 30,
        serving_min: 2,
      };

      const result = await addRecipe(recipeData as any);

      // Should return null (not created)
      expect(result).toBeNull();

      // Should store duplicate info
      const state = useRecipeStore.getState();
      expect(state.duplicateInfo).not.toBeNull();
      expect(state.duplicateInfo?.existing_recipe_id).toBe('existing-123');
      expect(state.pendingRecipeData).toEqual(recipeData);
    });

    it('stores similar recipes in duplicate info', async () => {
      const similarRecipes = [
        { id: 'sim-1', name: 'Similar Recipe 1', similarity: 0.85 },
        { id: 'sim-2', name: 'Similar Recipe 2', similarity: 0.72 },
      ];

      const duplicateError = {
        status: 409,
        response: {
          detail: {
            message: 'Similar recipes found',
            existing_recipe_id: null,
            similar_recipes: similarRecipes,
            hint: 'Use force=true',
          },
        },
      };

      vi.mocked(apiCreateRecipe).mockRejectedValue(duplicateError);
      vi.mocked(extractDuplicateInfo).mockReturnValue({
        message: 'Similar recipes found',
        existing_recipe_id: null,
        similar_recipes: similarRecipes,
        hint: 'Use force=true',
      });

      const { addRecipe } = useRecipeStore.getState();
      await addRecipe({ title: 'Test' } as any);

      const state = useRecipeStore.getState();
      expect(state.duplicateInfo?.similar_recipes).toHaveLength(2);
      expect(state.duplicateInfo?.similar_recipes?.[0].similarity).toBe(0.85);
    });

    it('creates recipe successfully when no duplicate', async () => {
      const createdRecipe = {
        ...baseRecipe,
        id: 'new-123',
        title: 'New Unique Recipe',
      };

      vi.mocked(apiCreateRecipe).mockResolvedValue(createdRecipe as any);
      vi.mocked(getAllRecipes).mockResolvedValue([createdRecipe] as any);

      const { addRecipe } = useRecipeStore.getState();
      const result = await addRecipe({
        title: 'New Unique Recipe',
      } as any);

      expect(result).not.toBeNull();
      expect(result?.title).toBe('New Unique Recipe');

      // No duplicate info should be set
      const state = useRecipeStore.getState();
      expect(state.duplicateInfo).toBeNull();
    });
  });

  describe('forceCreateRecipe', () => {
    it('creates recipe with force flag using pending data', async () => {
      const { setState, getState } = useRecipeStore as unknown as {
        setState: (partial: any) => void;
        getState: () => any;
      };

      const pendingData = {
        title: 'Duplicate Recipe',
        description: 'Force created',
        ingredients: [],
        instructions: [],
        prep_time_minutes: 10,
        cook_time_minutes: 20,
        total_time_minutes: 30,
        serving_min: 2,
      };

      // Set pending recipe data
      setState({
        pendingRecipeData: pendingData,
        duplicateInfo: {
          message: 'Duplicate found',
          existing_recipe_id: 'existing-123',
          hint: 'Force create',
        },
      });

      const createdRecipe = {
        ...baseRecipe,
        id: 'forced-123',
        title: 'Duplicate Recipe',
      };

      vi.mocked(apiCreateRecipe).mockResolvedValue(createdRecipe as any);
      vi.mocked(getAllRecipes).mockResolvedValue([createdRecipe] as any);

      const { forceCreateRecipe } = getState();
      const result = await forceCreateRecipe();

      // Should call API with force flag
      expect(apiCreateRecipe).toHaveBeenCalledWith(pendingData, {
        force: true,
      });
      expect(result?.id).toBe('forced-123');

      // Should clear duplicate state
      const finalState = getState();
      expect(finalState.duplicateInfo).toBeNull();
      expect(finalState.pendingRecipeData).toBeNull();
    });

    it('returns null if no pending data', async () => {
      const { setState, getState } = useRecipeStore as unknown as {
        setState: (partial: any) => void;
        getState: () => any;
      };

      // No pending data
      setState({
        pendingRecipeData: null,
        duplicateInfo: null,
      });

      const { forceCreateRecipe } = getState();
      const result = await forceCreateRecipe();

      expect(result).toBeNull();
      expect(apiCreateRecipe).not.toHaveBeenCalled();
    });
  });
});
