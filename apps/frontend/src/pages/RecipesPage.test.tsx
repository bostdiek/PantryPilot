import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import RecipesPage from './RecipesPage';

// Mock SVG import
vi.mock('../components/ui/icons/chef-hat.svg?react', () => ({
  default: () => <div data-testid="mock-chef-hat-icon" />,
}));

// Mock search icon
vi.mock('../components/ui/icons/search.svg?react', () => ({
  default: () => <div data-testid="mock-search-icon" />,
}));

// Mock chevron icon used by Select component
vi.mock('../components/ui/icons/chevron-up-down.svg?react', () => ({
  default: () => <div data-testid="mock-chevron-icon" />,
}));

// Mock window.matchMedia for media query hooks
const mockMatchMedia = vi.fn();
beforeEach(() => {
  mockMatchMedia.mockImplementation((query) => ({
    matches: false, // Default to desktop/non-mobile
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: mockMatchMedia,
  });
});

// Mock the store
const fetchRecipesMock = vi.fn();
const setPageMock = vi.fn();
vi.mock('../stores/useRecipeStore', () => ({
  useRecipeStore: () => ({
    recipes: [],
    filteredRecipes: [],
    isLoading: false,
    error: null,
    pagination: {
      page: 1,
      pageSize: 24,
      total: 0,
    },
    fetchRecipes: fetchRecipesMock,
    setPage: setPageMock,
  }),
}));

// Mock the filters hook
vi.mock('../hooks/useRecipeFilters', () => ({
  useRecipeFilters: () => ({
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
    setFilters: vi.fn(),
    setSortBy: vi.fn(),
    clearFilters: vi.fn(),
  }),
}));

describe('RecipesPage', () => {
  test('renders header and add button', () => {
    render(
      <MemoryRouter>
        <RecipesPage />
      </MemoryRouter>
    );

    expect(
      screen.getByRole('heading', { name: /my recipes/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /\+ add recipe/i })
    ).toBeInTheDocument();
  });

  test('renders empty state when no recipes', () => {
    render(
      <MemoryRouter>
        <RecipesPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/no recipes yet/i)).toBeInTheDocument();
    expect(
      screen.getByText(/start by adding your first recipe/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /add your first recipe/i })
    ).toBeInTheDocument();
  });
});
