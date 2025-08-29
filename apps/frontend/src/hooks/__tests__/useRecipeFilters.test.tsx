import { act, renderHook, waitFor } from '@testing-library/react';
import { MemoryRouter, useSearchParams } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { useRecipeStore } from '../../stores/useRecipeStore';
import { useRecipeFilters } from '../useRecipeFilters';

function Wrapper({
  initialEntries = [
    '/recipes?q=chicken&categories=dinner,dessert&difficulties=easy,c\u00f6mplex&cookTimeMin=5&cookTimeMax=30&include=rice,onion&exclude=peanut&sort=title-asc',
  ],
  children,
}: any) {
  return (
    <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
  );
}

describe('useRecipeFilters', () => {
  beforeEach(() => {
    act(() => {
      useRecipeStore.setState((state) => ({
        ...state,
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
      }));
    });
  });
  it('parses URL into filter state and sets sort', () => {
    const { result } = renderHook(
      () => ({
        filtersHook: useRecipeFilters(),
        paramsHook: useSearchParams(),
      }),
      {
        wrapper: ({ children }) => <Wrapper>{children}</Wrapper>,
      }
    );

    const { filters, sortBy } = result.current.filtersHook;
    // Categories should exclude invalid values; difficulties likewise
    expect(filters.query).toBe('chicken');
    expect(filters.categories).toEqual(['dinner', 'dessert']);
    expect(filters.difficulties).toEqual(['easy']);
    expect(filters.cookTimeMin).toBe(5);
    expect(filters.cookTimeMax).toBe(30);
    expect(filters.includedIngredients).toEqual(['rice', 'onion']);
    expect(filters.excludedIngredients).toEqual(['peanut']);
    expect(sortBy).toBe('title-asc');
  });

  it('updates URL when setting filters and sort', async () => {
    const { result } = renderHook(
      () => ({
        filtersHook: useRecipeFilters(),
        paramsHook: useSearchParams(),
      }),
      {
        wrapper: ({ children }) => (
          <Wrapper initialEntries={['/recipes']}>{children}</Wrapper>
        ),
      }
    );

    // Update filters and sort wrapped in act
    act(() => {
      result.current.filtersHook.setFilters({
        query: 'soup',
        categories: ['dinner'],
        difficulties: ['easy'],
        cookTimeMin: 10,
        cookTimeMax: 120,
        includedIngredients: ['onion'],
        excludedIngredients: ['peanut'],
      });
      result.current.filtersHook.setSortBy('cook-time-desc');
    });

    await waitFor(() => {
      const [params] = result.current.paramsHook;
      expect(params.get('q')).toBe('soup');
      expect(params.get('categories')).toBe('dinner');
      expect(params.get('difficulties')).toBe('easy');
      expect(params.get('cookTimeMin')).toBe('10');
      expect(params.get('cookTimeMax')).toBe('120');
      expect(params.get('include')).toBe('onion');
      expect(params.get('exclude')).toBe('peanut');
      expect(params.get('sort')).toBe('cook-time-desc');
    });

    // Clear filters resets URL (wrap in act and wait for router to update)
    act(() => {
      result.current.filtersHook.clearFilters();
    });
    await waitFor(() => {
      const [paramsAfterClear] = result.current.paramsHook;
      expect([...paramsAfterClear.keys()]).toEqual([]);
    });
  });
});
