import { act } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import type { Recipe } from '../../types/Recipe';
import { useRecipeStore } from '../useRecipeStore';

function makeRecipe(partial: Partial<Recipe>): Recipe {
  const base: Recipe = {
    id: 'r1',
    title: 'Pasta Primavera',
    description: 'Fresh veggies and pasta',
    ingredients: [
      { id: 'i1', name: 'pasta', quantity_value: 1, quantity_unit: 'lb' },
      { id: 'i2', name: 'tomato', quantity_value: 2, quantity_unit: 'pcs' },
    ],
    instructions: ['Boil', 'Mix'],
    prep_time_minutes: 10,
    cook_time_minutes: 20,
    serving_min: 4,
    difficulty: 'easy',
    category: 'dinner',
    total_time_minutes: 30,
    created_at: new Date('2025-01-01T00:00:00Z'),
    updated_at: new Date('2025-01-01T00:00:00Z'),
  };
  return { ...base, ...partial } as Recipe;
}

describe('useRecipeStore filtering and sorting', () => {
  beforeEach(() => {
    // Reset store state before each test
    act(() => {
      useRecipeStore.setState({
        recipes: [],
        filteredRecipes: [],
        isLoading: false,
        error: null,
        filters: {
          query: '',
          categories: [],
          difficulties: [],
          cookTimeMin: 0,
          cookTimeMax: 240,
          includedIngredients: [],
          excludedIngredients: [],
        },
        sortBy: 'relevance',
        pagination: { page: 1, pageSize: 24, total: 0 },
      });
    });
  });

  it('filters by query in title and ingredients', () => {
    const r1 = makeRecipe({
      id: '1',
      title: 'Chocolate Cake',
      ingredients: [
        { id: 'x', name: 'cocoa', quantity_value: 1, quantity_unit: 'cup' },
      ],
    });
    const r2 = makeRecipe({ id: '2', title: 'Tomato Soup' });
    act(() => {
      useRecipeStore.setState({ recipes: [r1, r2] });
      useRecipeStore.getState().setFilters({ query: 'cocoa' });
    });
    const { filteredRecipes, pagination } = useRecipeStore.getState();
    expect(filteredRecipes.map((r) => r.id)).toEqual(['1']);
    expect(pagination.total).toBe(1);
  });

  it('applies category and difficulty filters', () => {
    const r1 = makeRecipe({ id: '1', category: 'dessert', difficulty: 'easy' });
    const r2 = makeRecipe({ id: '2', category: 'dinner', difficulty: 'hard' });
    act(() => {
      useRecipeStore.setState({ recipes: [r1, r2] });
      useRecipeStore
        .getState()
        .setFilters({ categories: ['dessert'], difficulties: ['easy'] });
    });
    const { filteredRecipes } = useRecipeStore.getState();
    expect(filteredRecipes.map((r) => r.id)).toEqual(['1']);
  });

  it('filters by cook time range with null-safe fields', () => {
    const withNullTimes = makeRecipe({
      id: 'n',
      prep_time_minutes: undefined as unknown as number,
      cook_time_minutes: undefined as unknown as number,
    });
    const fast = makeRecipe({
      id: 'f',
      prep_time_minutes: 5,
      cook_time_minutes: 5,
    });
    const slow = makeRecipe({
      id: 's',
      prep_time_minutes: 100,
      cook_time_minutes: 50,
    });
    act(() => {
      useRecipeStore.setState({ recipes: [withNullTimes, fast, slow] });
      useRecipeStore.getState().setFilters({ cookTimeMin: 0, cookTimeMax: 15 });
    });
    const { filteredRecipes } = useRecipeStore.getState();
    // withNullTimes => total 0, fast => 10, slow => 150; range 0..15 keeps first two
    expect(filteredRecipes.map((r) => r.id).sort()).toEqual(['f', 'n']);
  });

  it('includes and excludes ingredients', () => {
    const egg = makeRecipe({
      id: 'egg',
      ingredients: [
        { id: 'i', name: 'egg', quantity_value: 2, quantity_unit: 'pcs' },
      ],
    });
    const milk = makeRecipe({
      id: 'milk',
      ingredients: [
        { id: 'j', name: 'milk', quantity_value: 1, quantity_unit: 'cup' },
      ],
    });
    act(() => {
      useRecipeStore.setState({ recipes: [egg, milk] });
      useRecipeStore.getState().setFilters({
        includedIngredients: ['egg'],
        excludedIngredients: ['milk'],
      });
    });
    const { filteredRecipes } = useRecipeStore.getState();
    expect(filteredRecipes.map((r) => r.id)).toEqual(['egg']);
  });

  it('sorts by cook time asc/desc with null-safe values', () => {
    const a = makeRecipe({
      id: 'a',
      prep_time_minutes: 5,
      cook_time_minutes: 5,
    }); // 10
    const b = makeRecipe({
      id: 'b',
      prep_time_minutes: 0,
      cook_time_minutes: 20,
    }); // 20
    const c = makeRecipe({
      id: 'c',
      prep_time_minutes: undefined as unknown as number,
      cook_time_minutes: undefined as unknown as number,
    }); // 0
    act(() => {
      useRecipeStore.setState({ recipes: [a, b, c] });
      useRecipeStore.getState().applyFiltersAndSort();
    });

    act(() => useRecipeStore.getState().setSortBy('cook-time-asc'));
    expect(useRecipeStore.getState().filteredRecipes.map((r) => r.id)).toEqual([
      'c',
      'a',
      'b',
    ]);

    act(() => useRecipeStore.getState().setSortBy('cook-time-desc'));
    expect(useRecipeStore.getState().filteredRecipes.map((r) => r.id)).toEqual([
      'b',
      'a',
      'c',
    ]);
  });
});
