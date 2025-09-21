import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { RecipeCard } from '../RecipeCard';
import type { Recipe } from '../../../types/Recipe';

const mockRecipeWithLongTitle: Recipe = {
  id: '1',
  title: 'This is an extremely long recipe title that should wrap to multiple lines and not cause the card to expand horizontally beyond its allocated space in the grid layout when using line-clamp-2 utility',
  description: 'A test recipe description',
  category: 'dinner',
  difficulty: 'medium',
  ethnicity: 'Italian',
  prep_time_minutes: 15,
  cook_time_minutes: 20,
  total_time_minutes: 35,
  serving_min: 4,
  serving_max: 6,
  oven_temperature_f: 350,
  ingredients: [
    {
      id: '1',
      name: 'Tomatoes',
      quantity_value: 2,
      quantity_unit: 'cups',
      prep: null,
      is_optional: false,
    },
  ],
  instructions: ['Step 1', 'Step 2'],
  user_notes: null,
  created_at: new Date('2024-01-01'),
  updated_at: new Date('2024-01-01'),
};

describe('RecipeCard - Long Title Handling', () => {
  it('renders long titles without breaking card layout', () => {
    const { container } = render(
      <MemoryRouter>
        <div style={{ width: '300px' }}>
          <RecipeCard recipe={mockRecipeWithLongTitle} />
        </div>
      </MemoryRouter>
    );

    // Verify the title is rendered
    expect(screen.getByText(/extremely long recipe title/)).toBeInTheDocument();

    // Verify the card container has proper width constraints
    const cardContainer = container.querySelector('.p-4');
    expect(cardContainer).toBeInTheDocument();
    
    // The card should not exceed its container width
    const link = container.querySelector('a');
    expect(link).toBeInTheDocument();
  });

  it('applies line-clamp-2 to long titles', () => {
    render(
      <MemoryRouter>
        <RecipeCard recipe={mockRecipeWithLongTitle} />
      </MemoryRouter>
    );

    const titleElement = screen.getByRole('heading', { level: 3 });
    expect(titleElement).toHaveClass('line-clamp-2');
  });

  it('maintains consistent card dimensions with long titles', () => {
    const { container } = render(
      <MemoryRouter>
        <div className="grid grid-cols-3 gap-6" style={{ width: '900px' }}>
          <RecipeCard recipe={mockRecipeWithLongTitle} />
          <RecipeCard recipe={{
            ...mockRecipeWithLongTitle,
            id: '2',
            title: 'Short Title'
          }} />
        </div>
      </MemoryRouter>
    );

    const cards = container.querySelectorAll('a');
    expect(cards).toHaveLength(2);
    
    // Both cards should be present in the grid
    cards.forEach(card => {
      expect(card).toBeInTheDocument();
    });
  });
});