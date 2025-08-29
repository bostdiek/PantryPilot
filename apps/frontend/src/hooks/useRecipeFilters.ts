import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  useRecipeStore,
  type RecipeFilters,
  type RecipeSortOption,
} from '../stores/useRecipeStore';
import {
  RECIPE_CATEGORIES,
  RECIPE_DIFFICULTIES,
  type RecipeCategory,
  type RecipeDifficulty,
} from '../types/Recipe';

/**
 * Custom hook for managing recipe filters with URL query parameters
 * Provides functions to sync filters and sort options with URL state
 */
export function useRecipeFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { filters, sortBy, setFilters, setSortBy, clearFilters } =
    useRecipeStore();

  // Parse URL parameters into filters
  const parseFiltersFromUrl = useCallback((): Partial<RecipeFilters> => {
    const urlFilters: Partial<RecipeFilters> = {};

    const query = searchParams.get('q');
    if (query) urlFilters.query = query;

    const categories = searchParams.get('categories');
    if (categories) {
      urlFilters.categories = categories
        .split(',')
        .filter((cat): cat is RecipeCategory =>
          RECIPE_CATEGORIES.includes(cat as RecipeCategory)
        );
    }

    const difficulties = searchParams.get('difficulties');
    if (difficulties) {
      urlFilters.difficulties = difficulties
        .split(',')
        .filter((diff): diff is RecipeDifficulty =>
          RECIPE_DIFFICULTIES.includes(diff as RecipeDifficulty)
        );
    }

    const cookTimeMin = searchParams.get('cookTimeMin');
    if (cookTimeMin) {
      const min = parseInt(cookTimeMin, 10);
      if (!isNaN(min)) urlFilters.cookTimeMin = min;
    }

    const cookTimeMax = searchParams.get('cookTimeMax');
    if (cookTimeMax) {
      const max = parseInt(cookTimeMax, 10);
      if (!isNaN(max)) urlFilters.cookTimeMax = max;
    }

    const includedIngredients = searchParams.get('include');
    if (includedIngredients) {
      urlFilters.includedIngredients = includedIngredients
        .split(',')
        .filter(Boolean);
    }

    const excludedIngredients = searchParams.get('exclude');
    if (excludedIngredients) {
      urlFilters.excludedIngredients = excludedIngredients
        .split(',')
        .filter(Boolean);
    }

    return urlFilters;
  }, [searchParams]);

  // Parse sort option from URL
  const parseSortFromUrl = useCallback((): RecipeSortOption => {
    const sort = searchParams.get('sort') as RecipeSortOption;
    const validSorts: RecipeSortOption[] = [
      'relevance',
      'title-asc',
      'title-desc',
      'cook-time-asc',
      'cook-time-desc',
      'recently-added',
    ];

    return validSorts.includes(sort) ? sort : 'relevance';
  }, [searchParams]);

  // Update URL with current filters and sort
  const updateUrl = (
    newFilters?: Partial<RecipeFilters>,
    newSort?: RecipeSortOption
  ) => {
    // Pull latest filters from the store to avoid stale closure during rapid successive updates
    const latest = useRecipeStore.getState().filters;
    const currentFilters = { ...latest, ...newFilters };
    const currentSort = newSort || sortBy;

    const newParams = new URLSearchParams();

    // Add query parameter
    if (currentFilters.query?.trim()) {
      newParams.set('q', currentFilters.query.trim());
    }

    // Add category filter
    if (currentFilters.categories && currentFilters.categories.length > 0) {
      newParams.set('categories', currentFilters.categories.join(','));
    }

    // Add difficulty filter
    if (currentFilters.difficulties && currentFilters.difficulties.length > 0) {
      newParams.set('difficulties', currentFilters.difficulties.join(','));
    }

    // Add cook time filters (only if not default values)
    if (currentFilters.cookTimeMin && currentFilters.cookTimeMin > 0) {
      newParams.set('cookTimeMin', currentFilters.cookTimeMin.toString());
    }
    if (currentFilters.cookTimeMax && currentFilters.cookTimeMax < 240) {
      newParams.set('cookTimeMax', currentFilters.cookTimeMax.toString());
    }

    // Add ingredient filters
    if (
      currentFilters.includedIngredients &&
      currentFilters.includedIngredients.length > 0
    ) {
      newParams.set('include', currentFilters.includedIngredients.join(','));
    }
    if (
      currentFilters.excludedIngredients &&
      currentFilters.excludedIngredients.length > 0
    ) {
      newParams.set('exclude', currentFilters.excludedIngredients.join(','));
    }

    // Add sort parameter (only if not default)
    if (currentSort !== 'relevance') {
      newParams.set('sort', currentSort);
    }

    setSearchParams(newParams, { replace: true });
  };

  // Load filters from URL on mount
  useEffect(() => {
    const urlFilters = parseFiltersFromUrl();
    const urlSort = parseSortFromUrl();

    // Only update if there are actual URL parameters
    if (Object.keys(urlFilters).length > 0 || urlSort !== 'relevance') {
      setFilters(urlFilters);
      if (urlSort !== 'relevance') {
        setSortBy(urlSort);
      }
    }
  }, [parseFiltersFromUrl, parseSortFromUrl, setFilters, setSortBy]);

  // Custom filter setters that also update URL
  const setFiltersWithUrl = (newFilters: Partial<RecipeFilters>) => {
    setFilters(newFilters);
    updateUrl(newFilters);
  };

  const setSortByWithUrl = (newSort: RecipeSortOption) => {
    setSortBy(newSort);
    updateUrl(undefined, newSort);
  };

  const clearFiltersWithUrl = () => {
    clearFilters();
    setSearchParams(new URLSearchParams(), { replace: true });
  };

  return {
    filters,
    sortBy,
    setFilters: setFiltersWithUrl,
    setSortBy: setSortByWithUrl,
    clearFilters: clearFiltersWithUrl,
    updateUrl,
  };
}
