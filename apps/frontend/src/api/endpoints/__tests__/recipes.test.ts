import { describe, expect, it } from 'vitest';
import {
  extractDuplicateInfo,
  isDuplicateRecipeError,
  type DuplicateRecipeError,
} from '../recipes';

describe('Duplicate Recipe Detection Utilities', () => {
  describe('isDuplicateRecipeError', () => {
    it('returns true for valid 409 error with detail object', () => {
      const error = {
        status: 409,
        response: {
          detail: {
            message: 'Recipe already exists',
            existing_recipe_id: 'abc-123',
            similar_recipes: [],
            hint: 'Use force=true to create anyway',
          },
        },
      };

      expect(isDuplicateRecipeError(error)).toBe(true);
    });

    it('returns true for 409 error with similar recipes', () => {
      const error = {
        status: 409,
        response: {
          detail: {
            message: 'Similar recipes found',
            existing_recipe_id: null,
            similar_recipes: [
              { id: 'sim-1', name: 'Similar Recipe', similarity: 0.85 },
            ],
            hint: 'Use force=true to create anyway',
          },
        },
      };

      expect(isDuplicateRecipeError(error)).toBe(true);
    });

    it('returns false for non-409 status', () => {
      const error = {
        status: 400,
        response: {
          detail: {
            message: 'Bad request',
            hint: 'Invalid data',
          },
        },
      };

      expect(isDuplicateRecipeError(error)).toBe(false);
    });

    it('returns false for 409 without proper detail structure', () => {
      const error = {
        status: 409,
        response: {
          detail: 'Just a string error',
        },
      };

      expect(isDuplicateRecipeError(error)).toBe(false);
    });

    it('returns false for null error', () => {
      expect(isDuplicateRecipeError(null)).toBe(false);
    });

    it('returns false for undefined error', () => {
      expect(isDuplicateRecipeError(undefined)).toBe(false);
    });

    it('returns false for non-object error', () => {
      expect(isDuplicateRecipeError('string error')).toBe(false);
      expect(isDuplicateRecipeError(123)).toBe(false);
    });

    it('returns false for 409 without response', () => {
      const error = {
        status: 409,
      };

      expect(isDuplicateRecipeError(error)).toBe(false);
    });

    it('returns true for edge case where response is the detail', () => {
      const error = {
        status: 409,
        response: {
          message: 'Recipe already exists',
          hint: 'Use force=true',
        },
      };

      expect(isDuplicateRecipeError(error)).toBe(true);
    });
  });

  describe('extractDuplicateInfo', () => {
    it('extracts duplicate info from valid error', () => {
      const duplicateInfo: DuplicateRecipeError = {
        message: 'Recipe already exists',
        existing_recipe_id: 'abc-123',
        similar_recipes: [],
        hint: 'Use force=true to create anyway',
      };

      const error = {
        status: 409,
        response: {
          detail: duplicateInfo,
        },
      };

      const result = extractDuplicateInfo(error);

      expect(result).toEqual(duplicateInfo);
      expect(result?.existing_recipe_id).toBe('abc-123');
    });

    it('extracts similar recipes from error', () => {
      const similarRecipes = [
        { id: 'sim-1', name: 'Similar Recipe 1', similarity: 0.85 },
        { id: 'sim-2', name: 'Similar Recipe 2', similarity: 0.72 },
      ];

      const duplicateInfo: DuplicateRecipeError = {
        message: 'Similar recipes found',
        existing_recipe_id: null,
        similar_recipes: similarRecipes,
        hint: 'Use force=true to create anyway',
      };

      const error = {
        status: 409,
        response: {
          detail: duplicateInfo,
        },
      };

      const result = extractDuplicateInfo(error);

      expect(result?.similar_recipes).toHaveLength(2);
      expect(result?.similar_recipes?.[0].name).toBe('Similar Recipe 1');
      expect(result?.similar_recipes?.[0].similarity).toBe(0.85);
    });

    it('returns null for non-duplicate error', () => {
      const error = {
        status: 400,
        response: {
          detail: { message: 'Bad request' },
        },
      };

      expect(extractDuplicateInfo(error)).toBeNull();
    });

    it('returns null for null error', () => {
      expect(extractDuplicateInfo(null)).toBeNull();
    });

    it('returns null for undefined error', () => {
      expect(extractDuplicateInfo(undefined)).toBeNull();
    });

    it('handles edge case where response is the detail', () => {
      const error = {
        status: 409,
        response: {
          message: 'Recipe exists',
          existing_recipe_id: 'edge-123',
          hint: 'Force create',
        },
      };

      const result = extractDuplicateInfo(error);

      expect(result?.message).toBe('Recipe exists');
      expect(result?.existing_recipe_id).toBe('edge-123');
    });
  });
});

describe('DuplicateRecipeError Type', () => {
  it('should have correct shape for exact match', () => {
    const error: DuplicateRecipeError = {
      message: 'Exact match found',
      existing_recipe_id: 'recipe-123',
      similar_recipes: undefined,
      hint: 'View existing recipe',
    };

    expect(error.message).toBeDefined();
    expect(error.hint).toBeDefined();
    expect(error.existing_recipe_id).toBe('recipe-123');
  });

  it('should have correct shape for similar matches', () => {
    const error: DuplicateRecipeError = {
      message: 'Similar recipes found',
      existing_recipe_id: null,
      similar_recipes: [
        { id: '1', name: 'Recipe 1', similarity: 0.9 },
        { id: '2', name: 'Recipe 2', similarity: 0.8 },
      ],
      hint: 'Select existing or create anyway',
    };

    expect(error.similar_recipes).toHaveLength(2);
    expect(error.existing_recipe_id).toBeNull();
  });
});
