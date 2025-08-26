import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, test, vi } from 'vitest';
import RecipesPage from './RecipesPage';

// Mock SVG import
vi.mock('../components/ui/icons/chef-hat.svg?react', () => ({
  default: () => <div data-testid="mock-chef-hat-icon" />,
}));

// Mock the store
const fetchRecipesMock = vi.fn();
vi.mock('../stores/useRecipeStore', () => ({
  useRecipeStore: () => ({
    recipes: [],
    isLoading: false,
    fetchRecipes: fetchRecipesMock,
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
