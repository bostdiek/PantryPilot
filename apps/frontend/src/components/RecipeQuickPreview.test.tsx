import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RecipeQuickPreview } from './RecipeQuickPreview';
import type { Recipe } from '../types/Recipe';

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockRecipe: Recipe = {
  id: 'recipe-1',
  title: 'Test Recipe',
  description: 'A delicious test recipe',
  ingredients: [
    {
      id: 'ing-1',
      name: 'Tomatoes',
      quantity_value: 2,
      quantity_unit: 'cups',
    },
    {
      id: 'ing-2',
      name: 'Onions',
      quantity_value: 1,
      quantity_unit: 'large',
    },
    {
      id: 'ing-3',
      name: 'Garlic',
      quantity_value: 3,
      quantity_unit: 'cloves',
    },
    {
      id: 'ing-4',
      name: 'Bell Pepper',
      quantity_value: 1,
      quantity_unit: 'medium',
    },
    {
      id: 'ing-5',
      name: 'Olive Oil',
      quantity_value: 2,
      quantity_unit: 'tbsp',
    },
    {
      id: 'ing-6',
      name: 'Salt',
      quantity_value: 1,
      quantity_unit: 'tsp',
    },
  ],
  instructions: ['Step 1', 'Step 2', 'Step 3'],
  prep_time_minutes: 15,
  cook_time_minutes: 30,
  total_time_minutes: 45,
  serving_min: 4,
  serving_max: 6,
  difficulty: 'medium',
  category: 'dinner',
  created_at: new Date('2023-01-01'),
  updated_at: new Date('2023-01-01'),
};

describe('RecipeQuickPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders recipe details correctly', () => {
    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={vi.fn()}
          recipe={mockRecipe}
        />
      </MemoryRouter>
    );

    // Check for title (appears in both desktop and mobile)
    expect(screen.getAllByText('Test Recipe')).toHaveLength(2);
    expect(screen.getAllByText('A delicious test recipe')).toHaveLength(2);
    expect(screen.getAllByText('45')).toHaveLength(2);

    // Check for ingredients section
    expect(screen.getAllByText('Ingredients')).toHaveLength(2);
    expect(screen.getAllByText('Tomatoes')).toHaveLength(2);
  });

  it('displays limited ingredients with more indicator', () => {
    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={vi.fn()}
          recipe={mockRecipe}
        />
      </MemoryRouter>
    );

    // Should show first 5 ingredients
    expect(screen.getAllByText('Tomatoes')).toHaveLength(2);
    expect(screen.getAllByText('Olive Oil')).toHaveLength(2);

    // Should not show 6th ingredient
    expect(screen.queryByText('Salt')).not.toBeInTheDocument();

    // Should show more ingredients indicator
    expect(screen.getAllByText('+1 more ingredients')).toHaveLength(2);
  });

  it('renders action buttons correctly', () => {
    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={vi.fn()}
          recipe={mockRecipe}
          onRemoveFromDay={vi.fn()}
        />
      </MemoryRouter>
    );

    // Should have action buttons (2 sets for desktop/mobile)
    expect(screen.getAllByText('View Full Recipe')).toHaveLength(2);
    expect(screen.getAllByText('Remove from Day')).toHaveLength(2);
  });

  it('does not render remove button when onRemoveFromDay is not provided', () => {
    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={vi.fn()}
          recipe={mockRecipe}
        />
      </MemoryRouter>
    );

    expect(screen.queryByText('Remove from Day')).not.toBeInTheDocument();
  });

  it('does not render when recipe is null', () => {
    const { container } = render(
      <MemoryRouter>
        <RecipeQuickPreview isOpen={true} onClose={vi.fn()} recipe={null} />
      </MemoryRouter>
    );

    expect(container.firstChild).toBeNull();
  });

  it('handles basic interactions', async () => {
    const onCloseMock = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={onCloseMock}
          recipe={mockRecipe}
        />
      </MemoryRouter>
    );

    // Should be able to close with escape key
    await user.keyboard('{Escape}');
    expect(onCloseMock).toHaveBeenCalled();
  });

  it('handles recipe with fewer ingredients', () => {
    const recipeFewerIngredients = {
      ...mockRecipe,
      ingredients: mockRecipe.ingredients.slice(0, 3),
    };

    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={vi.fn()}
          recipe={recipeFewerIngredients}
        />
      </MemoryRouter>
    );

    expect(screen.getAllByText('Tomatoes')).toHaveLength(2);
    expect(screen.getAllByText('Garlic')).toHaveLength(2);
    expect(screen.queryByText('+1 more ingredients')).not.toBeInTheDocument();
  });

  it('navigates to recipe detail when View Full Recipe is clicked', async () => {
    const onCloseMock = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={onCloseMock}
          recipe={mockRecipe}
          dateContext="2025-01-15"
        />
      </MemoryRouter>
    );

    // Click the View Full Recipe button (desktop version)
    const viewFullButtons = screen.getAllByText('View Full Recipe');
    await user.click(viewFullButtons[0]);

    // Should navigate with proper query params
    expect(mockNavigate).toHaveBeenCalledWith(
      '/recipes/recipe-1?from=mealplan&d=2025-01-15'
    );
    // Note: onClose is intentionally NOT called during navigation
    // The routing will unmount the dialog naturally
    expect(onCloseMock).not.toHaveBeenCalled();
  });

  it('calls onRemoveFromDay when Remove from Day is clicked', async () => {
    const onCloseMock = vi.fn();
    const onRemoveFromDayMock = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={onCloseMock}
          recipe={mockRecipe}
          onRemoveFromDay={onRemoveFromDayMock}
        />
      </MemoryRouter>
    );

    // Click the Remove from Day button (desktop version)
    const removeButtons = screen.getAllByText('Remove from Day');
    await user.click(removeButtons[0]);

    // Should call the remove function
    expect(onRemoveFromDayMock).toHaveBeenCalled();
    // Should not close the modal (parent handles closure)
    expect(onCloseMock).not.toHaveBeenCalled();
  });
});
