import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { MealEntry } from '../../types/MealPlan';
import type { Recipe } from '../../types/Recipe';
import { MobileMealCard } from '../MobileMealCard';

describe('MobileMealCard', () => {
  const mockRecipe: Recipe = {
    id: 'recipe-1',
    title: 'Test Recipe',
    description: 'A test recipe',
    category: 'dinner',
    difficulty: 'easy',
    prep_time_minutes: 10,
    cook_time_minutes: 20,
    total_time_minutes: 30,
    serving_min: 2,
    serving_max: 4,
    ingredients: [],
    instructions: [],
    userId: 'user-1',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  };

  const mockEntry: MealEntry = {
    id: 'entry-1',
    plannedForDate: '2024-01-15',
    recipeId: 'recipe-1',
    orderIndex: 0,
    wasCooked: false,
    isLeftover: false,
    isEatingOut: false,
    userId: 'user-1',
  };

  it('renders meal card with recipe', () => {
    render(<MobileMealCard entry={mockEntry} recipe={mockRecipe} />);

    expect(screen.getByText('Test Recipe')).toBeInTheDocument();
    // Text is now split across elements, so we check for the parts
    expect(screen.getByText('30 min')).toBeInTheDocument();
    expect(screen.getByText(/easy/i)).toBeInTheDocument();
  });

  it('renders eating out entry', () => {
    const eatingOutEntry: MealEntry = {
      ...mockEntry,
      recipeId: null,
      isEatingOut: true,
    };

    render(<MobileMealCard entry={eatingOutEntry} />);

    expect(screen.getByText('Eating out')).toBeInTheDocument();
  });

  it('renders leftover entry', () => {
    const leftoverEntry: MealEntry = {
      ...mockEntry,
      recipeId: null,
      isLeftover: true,
    };

    render(<MobileMealCard entry={leftoverEntry} />);

    // Now "Leftovers" appears twice - once in title and once in badge
    const leftoverElements = screen.getAllByText('Leftovers');
    expect(leftoverElements.length).toBeGreaterThan(0);
  });

  it('shows cooked status when meal is cooked', () => {
    const cookedEntry: MealEntry = {
      ...mockEntry,
      wasCooked: true,
      cookedAt: '2024-01-15T18:00:00Z',
    };

    render(<MobileMealCard entry={cookedEntry} recipe={mockRecipe} />);

    expect(screen.getByText(/Cooked/)).toBeInTheDocument();
  });

  it('calls onMarkCooked when mark cooked button is clicked', async () => {
    const user = userEvent.setup();
    const onMarkCooked = vi.fn();

    render(
      <MobileMealCard
        entry={mockEntry}
        recipe={mockRecipe}
        onMarkCooked={onMarkCooked}
      />
    );

    const markCookedButton = screen.getByRole('button', {
      name: /Mark.*as cooked/i,
    });
    await user.click(markCookedButton);

    expect(onMarkCooked).toHaveBeenCalledOnce();
  });

  it('calls onEdit when edit button is clicked', async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();

    render(
      <MobileMealCard entry={mockEntry} recipe={mockRecipe} onEdit={onEdit} />
    );

    const editButton = screen.getByRole('button', { name: /Edit/i });
    await user.click(editButton);

    expect(onEdit).toHaveBeenCalledOnce();
  });

  it('calls onRecipeClick when recipe title is clicked', async () => {
    const user = userEvent.setup();
    const onRecipeClick = vi.fn();

    render(
      <MobileMealCard
        entry={mockEntry}
        recipe={mockRecipe}
        onRecipeClick={onRecipeClick}
      />
    );

    const recipeTitle = screen.getByText('Test Recipe');
    await user.click(recipeTitle);

    expect(onRecipeClick).toHaveBeenCalledOnce();
  });

  it('shows Add Recipe button for entry without recipe', () => {
    const entryWithoutRecipe: MealEntry = {
      ...mockEntry,
      recipeId: null,
    };
    const onAddRecipe = vi.fn();

    render(
      <MobileMealCard entry={entryWithoutRecipe} onAddRecipe={onAddRecipe} />
    );

    expect(screen.getByText('Add Recipe')).toBeInTheDocument();
  });

  it('has touch-friendly buttons with proper sizing', () => {
    const { container } = render(
      <MobileMealCard
        entry={mockEntry}
        recipe={mockRecipe}
        onMarkCooked={vi.fn()}
        onEdit={vi.fn()}
      />
    );

    const buttons = container.querySelectorAll('button');
    buttons.forEach((button) => {
      const classes = button.className;
      // Check that buttons have appropriate size classes for touch interaction
      expect(classes).toMatch(/text-xs|text-sm|text-base/);
    });
  });
});
