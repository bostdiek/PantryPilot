import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, test, vi } from 'vitest';
import HomePage from './HomePage';

// Mock SVG imports
vi.mock('../components/ui/icons/kitchen.svg?react', () => ({
  default: () => <div data-testid="mock-kitchen-icon" />,
}));

vi.mock('../components/ui/icons/calendar.svg?react', () => ({
  default: () => <div data-testid="mock-calendar-icon" />,
}));

vi.mock('../components/ui/icons/restaurant.svg?react', () => ({
  default: () => <div data-testid="mock-restaurant-icon" />,
}));

vi.mock('../components/ui/icons/chef-hat.svg?react', () => ({
  default: () => <div data-testid="mock-chef-hat-icon" />,
}));

vi.mock('../components/ui/icons/chevron-right.svg?react', () => ({
  default: () => <div data-testid="mock-chevron-right-icon" />,
}));

// Mock the stores
vi.mock('../stores/useRecipeStore', () => ({
  useRecipeStore: () => ({
    recipes: [],
    isLoading: false,
    fetchRecipes: vi.fn(),
  }),
}));

vi.mock('../stores/useMealPlanStore', () => ({
  useMealPlanStore: () => ({
    currentWeek: null,
    isLoading: false,
    loadWeek: vi.fn(),
  }),
}));

vi.mock('../stores/useAuthStore', () => ({
  useDisplayName: () => 'Test User',
}));

describe('HomePage', () => {
  test('renders the welcome message', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    expect(screen.getByText('Hi, Test User!')).toBeInTheDocument();
    expect(screen.getByText('Ready to plan some meals?')).toBeInTheDocument();
  });

  test('renders the recipes count section', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    expect(screen.getAllByText('0')[0]).toBeInTheDocument();
    expect(screen.getByText('Recipes')).toBeInTheDocument();
  });

  test('renders the weekly plan count section', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    expect(screen.getByText('This Week')).toBeInTheDocument();
  });

  test("renders today's meals section", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    expect(screen.getByText("Today's Meals")).toBeInTheDocument();
    // With no currentWeek, show empty state
    expect(screen.getByText('No meals planned for today')).toBeInTheDocument();
    expect(screen.getByText("Plan Today's Meals")).toBeInTheDocument();
  });

  test('renders the quick actions section', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    expect(screen.getByText('Add New Recipe')).toBeInTheDocument();
    expect(screen.getByText('View Meal Planner')).toBeInTheDocument();
    expect(screen.getByText('Weekly Grocery List')).toBeInTheDocument();
  });
});
