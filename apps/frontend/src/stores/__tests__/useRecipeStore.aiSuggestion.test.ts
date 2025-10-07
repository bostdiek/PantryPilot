import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRecipeStore } from '../useRecipeStore';
import type { AIDraftPayload } from '../../types/AIDraft';
import type { RecipeCreate } from '../../types/Recipe';

// Mock the API
vi.mock('../../api/endpoints/recipes', () => ({
  getAllRecipes: vi.fn(() => Promise.resolve([])),
  getRecipeById: vi.fn(),
  createRecipe: vi.fn(),
  updateRecipe: vi.fn(),
  deleteRecipe: vi.fn(),
}));

describe('useRecipeStore - AI Suggestion', () => {
  beforeEach(() => {
    // Reset store state before each test
    const { result } = renderHook(() => useRecipeStore());
    act(() => {
      result.current.clearFormSuggestion();
    });
  });

  describe('setFormFromSuggestion', () => {
    it('sets formSuggestion when generated_recipe is present', () => {
      const { result } = renderHook(() => useRecipeStore());

      const recipeData: RecipeCreate = {
        title: 'AI Generated Recipe',
        description: 'Extracted from URL',
        ingredients: [
          {
            name: 'Flour',
            quantity_value: 2,
            quantity_unit: 'cups',
            prep: {},
            is_optional: false,
          },
        ],
        instructions: ['Mix ingredients', 'Bake at 350F'],
        prep_time_minutes: 10,
        cook_time_minutes: 30,
        serving_min: 4,
        difficulty: 'easy',
        category: 'dessert',
      };

      const payload: AIDraftPayload = {
        generated_recipe: {
          recipe_data: recipeData,
          confidence_score: 0.9,
          extraction_notes: null,
          source_url: 'https://example.com/recipe',
        },
        extraction_metadata: {
          source_url: 'https://example.com/recipe',
          extracted_at: '2025-10-03T19:03:34.543173+00:00',
          confidence_score: 0.9,
        },
      };

      act(() => {
        result.current.setFormFromSuggestion(payload);
      });

      expect(result.current.formSuggestion).toEqual(recipeData);
      expect(result.current.isAISuggestion).toBe(true);
    });

    it('clears formSuggestion but keeps isAISuggestion flag when extraction failed', () => {
      const { result } = renderHook(() => useRecipeStore());

      const payload: AIDraftPayload = {
        generated_recipe: null,
        extraction_metadata: {
          source_url: 'https://example.com/recipe',
          extracted_at: '2025-10-03T19:03:34.543173+00:00',
          failure: {
            reason: 'No recipe found',
          },
        },
      };

      act(() => {
        result.current.setFormFromSuggestion(payload);
      });

      expect(result.current.formSuggestion).toBeNull();
      expect(result.current.isAISuggestion).toBe(true);
    });

    it('handles payload with all optional fields', () => {
      const { result } = renderHook(() => useRecipeStore());

      const recipeData: RecipeCreate = {
        title: 'Simple Recipe',
        description: 'Basic recipe',
        ingredients: [],
        instructions: ['Step 1'],
        prep_time_minutes: 5,
        cook_time_minutes: 10,
        serving_min: 2,
        serving_max: 4,
        difficulty: 'medium',
        category: 'lunch',
        ethnicity: 'Italian',
        oven_temperature_f: 375,
        user_notes: 'From AI extraction',
        link_source: 'https://example.com/recipe',
      };

      const payload: AIDraftPayload = {
        generated_recipe: {
          recipe_data: recipeData,
          confidence_score: 0.85,
          extraction_notes: 'Good extraction',
          source_url: 'https://example.com/recipe',
        },
        extraction_metadata: {
          source_url: 'https://example.com/recipe',
          extracted_at: '2025-10-03T19:03:34.543173+00:00',
          confidence_score: 0.85,
        },
      };

      act(() => {
        result.current.setFormFromSuggestion(payload);
      });

      expect(result.current.formSuggestion).toEqual(recipeData);
      expect(result.current.formSuggestion?.ethnicity).toBe('Italian');
      expect(result.current.formSuggestion?.oven_temperature_f).toBe(375);
      expect(result.current.formSuggestion?.user_notes).toBe(
        'From AI extraction'
      );
      expect(result.current.formSuggestion?.link_source).toBe(
        'https://example.com/recipe'
      );
    });
  });

  describe('clearFormSuggestion', () => {
    it('clears formSuggestion and isAISuggestion flag', () => {
      const { result } = renderHook(() => useRecipeStore());

      const recipeData: RecipeCreate = {
        title: 'Test Recipe',
        description: 'Test',
        ingredients: [],
        instructions: [],
        prep_time_minutes: 0,
        cook_time_minutes: 0,
        serving_min: 1,
        difficulty: 'easy',
        category: 'dinner',
      };

      const payload: AIDraftPayload = {
        generated_recipe: {
          recipe_data: recipeData,
          confidence_score: 0.9,
          extraction_notes: null,
          source_url: 'https://example.com/recipe',
        },
        extraction_metadata: {
          source_url: 'https://example.com/recipe',
          extracted_at: '2025-10-03T19:03:34.543173+00:00',
          confidence_score: 0.9,
        },
      };

      // First set a suggestion
      act(() => {
        result.current.setFormFromSuggestion(payload);
      });

      expect(result.current.formSuggestion).not.toBeNull();
      expect(result.current.isAISuggestion).toBe(true);

      // Then clear it
      act(() => {
        result.current.clearFormSuggestion();
      });

      expect(result.current.formSuggestion).toBeNull();
      expect(result.current.isAISuggestion).toBe(false);
    });
  });

  describe('Integration with existing store state', () => {
    it('does not affect recipes list when setting form suggestion', () => {
      const { result } = renderHook(() => useRecipeStore());

      // Set some initial recipes (mocking existing state)
      const mockRecipes: any[] = [
        { id: '1', title: 'Existing Recipe 1' },
        { id: '2', title: 'Existing Recipe 2' },
      ];

      act(() => {
        useRecipeStore.setState({ recipes: mockRecipes });
      });

      expect(result.current.recipes).toHaveLength(2);

      // Now set a form suggestion
      const recipeData: RecipeCreate = {
        title: 'AI Recipe',
        description: 'Test',
        ingredients: [],
        instructions: [],
        prep_time_minutes: 0,
        cook_time_minutes: 0,
        serving_min: 1,
        difficulty: 'easy',
        category: 'dinner',
      };

      const payload: AIDraftPayload = {
        generated_recipe: {
          recipe_data: recipeData,
          confidence_score: 0.9,
          extraction_notes: null,
          source_url: 'https://example.com/recipe',
        },
        extraction_metadata: {
          source_url: 'https://example.com/recipe',
          extracted_at: '2025-10-03T19:03:34.543173+00:00',
          confidence_score: 0.9,
        },
      };

      act(() => {
        result.current.setFormFromSuggestion(payload);
      });

      // Recipes list should be unchanged
      expect(result.current.recipes).toHaveLength(2);
      expect(result.current.formSuggestion).not.toBeNull();
    });
  });
});
