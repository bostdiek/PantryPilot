import { beforeEach, describe, expect, it, vi } from 'vitest';

// Prevent createBrowserRouter side-effects when importing the router module
// by mocking only createBrowserRouter to a noop while preserving other exports.
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, createBrowserRouter: () => ({}) } as any;
});

// Mock logger to avoid noisy logs
vi.mock('../lib/logger', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), warn: vi.fn() },
}));

// Mock stores and API functions
let fetchRecipesMock = vi.fn();
let loadWeekMock = vi.fn();
let recipesArray: any[] = [];
let authToken: string | null = null;
let fetchByIdMock = vi.fn().mockResolvedValue({ id: 'r1' });
vi.mock('../stores/useRecipeStore', () => ({
  useRecipeStore: {
    getState: () => ({
      recipes: recipesArray,
      fetchRecipes: fetchRecipesMock,
      fetchRecipeById: fetchByIdMock,
      setFormFromSuggestion: vi.fn(),
    }),
  },
}));

vi.mock('../stores/useMealPlanStore', () => ({
  useMealPlanStore: {
    getState: () => ({ loadWeek: loadWeekMock }),
  },
}));

vi.mock('../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: () => ({ token: authToken }),
  },
}));

vi.mock('../api/endpoints/aiDrafts', () => ({
  getDraftById: vi.fn().mockResolvedValue({ payload: { title: 'AI' } }),
}));

import {
  homeLoader,
  mealPlanLoader,
  newRecipeLoader,
  recipeDetailLoader,
  recipesLoader,
} from '../routerConfig';

describe('routerConfig loaders', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchRecipesMock = vi.fn().mockResolvedValue(null);
    loadWeekMock = vi.fn().mockResolvedValue(null);
    recipesArray = [];
    authToken = null;
    fetchByIdMock = vi.fn().mockResolvedValue({ id: 'r1' });
  });

  it('homeLoader calls fetchRecipes and loadWeek', async () => {
    // update mocks in mocked module
    const { useRecipeStore } = await import('../stores/useRecipeStore');
    const { useMealPlanStore } = await import('../stores/useMealPlanStore');
    useRecipeStore.getState().fetchRecipes = fetchRecipesMock;
    useMealPlanStore.getState().loadWeek = loadWeekMock;

    await homeLoader();
    expect(fetchRecipesMock).toHaveBeenCalled();
    expect(loadWeekMock).toHaveBeenCalled();
  });

  it('recipesLoader fetches when recipes empty', async () => {
    // ensure the shared recipesArray is empty
    recipesArray = [];
    await recipesLoader();
    expect(fetchRecipesMock).toHaveBeenCalled();
  });

  it('recipesLoader skips fetch when recipes present', async () => {
    // set the shared recipesArray to simulate existing recipes
    recipesArray = [{ id: 'r1' } as any];
    await recipesLoader();
    expect(fetchRecipesMock).not.toHaveBeenCalled();
  });

  it('newRecipeLoader redirects to login when ai deep link and no auth token', async () => {
    const req = new Request(
      'http://localhost/recipes/new?ai=1&draftId=d1&token=t1'
    );
    const res = await newRecipeLoader({ request: req } as any);
    // Expect a redirect response (302) to login with next param
    expect(res).toHaveProperty('status');
    expect(res.status).toBe(302);
    const location = res.headers.get('location');
    expect(location).toContain('/login');
  });

  it('newRecipeLoader fetches draft when authenticated', async () => {
    // Mock auth token via shared authToken variable used in mocked module
    authToken = 'auth';
    const { getDraftById } = await import('../api/endpoints/aiDrafts');
    const req = new Request(
      'http://localhost/recipes/new?ai=1&draftId=d1&token=t1'
    );

    const result = await newRecipeLoader({ request: req } as any);
    expect(getDraftById).toHaveBeenCalledWith('d1', 't1');
    // result is null on success
    expect(result).toBeNull();
  });

  it('recipeDetailLoader calls fetchRecipeById when id param provided', async () => {
    // update the shared fetchByIdMock used by the mocked store
    fetchByIdMock = vi.fn().mockResolvedValue({ id: 'r2' });

    const res = await recipeDetailLoader({ params: { id: 'r2' } } as any);
    expect(fetchByIdMock).toHaveBeenCalledWith('r2');
    expect(res).toEqual({ id: 'r2' });
  });

  it('mealPlanLoader loads week and conditional recipes', async () => {
    const { useRecipeStore } = await import('../stores/useRecipeStore');
    const { useMealPlanStore } = await import('../stores/useMealPlanStore');
    useMealPlanStore.getState().loadWeek = loadWeekMock;
    useRecipeStore.getState().recipes = [];
    useRecipeStore.getState().fetchRecipes = fetchRecipesMock;

    await mealPlanLoader();
    expect(loadWeekMock).toHaveBeenCalled();
    expect(fetchRecipesMock).toHaveBeenCalled();
  });
});
