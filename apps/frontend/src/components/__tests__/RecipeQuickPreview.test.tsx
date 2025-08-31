import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RecipeQuickPreview } from '../RecipeQuickPreview';
import type { Recipe } from '../../types/Recipe';

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

    // Title appears twice (desktop + mobile)
    expect(screen.getAllByText('Test Recipe')).toHaveLength(2);
    expect(screen.getAllByText('A delicious test recipe')).toHaveLength(2);
    expect(screen.getAllByText('45')).toHaveLength(2);
    expect(screen.getAllByText('minutes')).toHaveLength(2);
    expect(screen.getAllByText('Medium')).toHaveLength(2);
    expect(screen.getAllByText('difficulty')).toHaveLength(2);
    expect(screen.getAllByText('4-6')).toHaveLength(2);
    expect(screen.getAllByText('servings')).toHaveLength(2);
  });

  it('displays first 5 ingredients', () => {
    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={vi.fn()}
          recipe={mockRecipe}
        />
      </MemoryRouter>
    );

    // Check for ingredients (there will be 2 of each due to desktop/mobile versions)
    expect(screen.getAllByText('Tomatoes')).toHaveLength(2);
    expect(screen.getAllByText('2 cups')).toHaveLength(2);
    expect(screen.getAllByText('Onions')).toHaveLength(2);
    expect(screen.getAllByText('1 large')).toHaveLength(2);
    expect(screen.getAllByText('Garlic')).toHaveLength(2);
    expect(screen.getAllByText('3 cloves')).toHaveLength(2);
    expect(screen.getAllByText('Bell Pepper')).toHaveLength(2);
    expect(screen.getAllByText('1 medium')).toHaveLength(2);
    expect(screen.getAllByText('Olive Oil')).toHaveLength(2);
    expect(screen.getAllByText('2 tbsp')).toHaveLength(2);

    // Should not display the 6th ingredient
    expect(screen.queryByText('Salt')).not.toBeInTheDocument();

    // Should show "+1 more ingredients" text (appears twice for desktop/mobile)
    expect(screen.getAllByText('+1 more ingredients')).toHaveLength(2);
  });

  it('calls onClose when close button is clicked on desktop', async () => {
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

    // Look for the close button (X icon) - this is only visible on desktop
    const closeButton = screen.getByLabelText('Close preview');
    await user.click(closeButton);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('navigates to full recipe view with context', async () => {
    const onCloseMock = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={onCloseMock}
          recipe={mockRecipe}
          dateContext="2023-12-25"
        />
      </MemoryRouter>
    );

    // Click the first "View Full Recipe" button (there are 2 - desktop and mobile)
    const viewFullButtons = screen.getAllByText('View Full Recipe');
    expect(viewFullButtons).toHaveLength(2);
    await user.click(viewFullButtons[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/recipes/recipe-1?from=mealplan&d=2023-12-25');
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('navigates to edit recipe', async () => {
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

    // Click the first "Edit" button (there are 2 - desktop and mobile)
    const editButtons = screen.getAllByText('Edit');
    expect(editButtons).toHaveLength(2);
    await user.click(editButtons[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/recipes/recipe-1/edit');
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('calls onRemoveFromDay when remove button is clicked', async () => {
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

    // Click the first remove button (there are 2 - desktop and mobile)
    const removeButtons = screen.getAllByText('Remove from Day');
    expect(removeButtons).toHaveLength(2);
    await user.click(removeButtons[0]);

    expect(onRemoveFromDayMock).toHaveBeenCalledTimes(1);
    expect(onCloseMock).toHaveBeenCalledTimes(1);
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

    // The component renders both desktop and mobile versions, but without onRemoveFromDay
    // there should be no "Remove from Day" buttons
    expect(screen.queryByText('Remove from Day')).not.toBeInTheDocument();
  });

  it('does not render when recipe is null', () => {
    const { container } = render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={vi.fn()}
          recipe={null}
        />
      </MemoryRouter>
    );

    expect(container.firstChild).toBeNull();
  });

  it('closes on Escape key press', async () => {
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

    await user.keyboard('{Escape}');

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('handles recipe with no description', () => {
    const recipeNoDescription = { ...mockRecipe, description: undefined };

    render(
      <MemoryRouter>
        <RecipeQuickPreview
          isOpen={true}
          onClose={vi.fn()}
          recipe={recipeNoDescription}
        />
      </MemoryRouter>
    );

    expect(screen.getAllByText('Test Recipe')).toHaveLength(2);
    expect(screen.queryByText('A delicious test recipe')).not.toBeInTheDocument();
  });

  it('handles recipe with less than 5 ingredients', () => {
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

    // Check for the 3 ingredients (appears twice due to desktop/mobile)
    expect(screen.getAllByText('Tomatoes')).toHaveLength(2);
    expect(screen.getAllByText('Onions')).toHaveLength(2);
    expect(screen.getAllByText('Garlic')).toHaveLength(2);
    expect(screen.queryByText('+1 more ingredients')).not.toBeInTheDocument();
  });
});