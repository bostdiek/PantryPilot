import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { RecipeCard } from '../RecipeCard';
import type { Recipe } from '../../../types/Recipe';

const mockRecipeWithLongTitle: Recipe = {
  id: '1',
  title:
    'This is an extremely long recipe title that should wrap to multiple lines and not cause the card to expand horizontally beyond its allocated space in the grid layout when using line-clamp-2 utility',
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
  created_at: '2024-01-01T00:00:00.000Z',
  updated_at: '2024-01-01T00:00:00.000Z',
};

describe('RecipeCard - Long Title Handling', () => {
  it('renders title and description without breaking card layout', () => {
    render(
      <MemoryRouter>
        <div style={{ width: '300px' }}>
          <RecipeCard recipe={mockRecipeWithLongTitle} />
        </div>
      </MemoryRouter>
    );

    // Verify the title is rendered using semantic queries
    const titleElement = screen.getByRole('heading', { level: 3 });
    expect(titleElement).toBeInTheDocument();
    expect(titleElement).toHaveTextContent(/extremely long recipe title/);

    // Verify the description is rendered
    expect(screen.getByText('A test recipe description')).toBeInTheDocument();

    // Get the link element (card wrapper) and check for overflow
    const linkElement = screen.getByRole('link');
    expect(linkElement).toBeInTheDocument();

    // Ensure the card does not overflow horizontally in JSDOM environment
    expect(linkElement.scrollWidth).toBeLessThanOrEqual(
      linkElement.clientWidth + 1
    ); // +1 for rounding
  });

  it('truncates long title with line clamp', () => {
    render(
      <MemoryRouter>
        <RecipeCard recipe={mockRecipeWithLongTitle} />
      </MemoryRouter>
    );

    const titleElement = screen.getByRole('heading', { level: 3 });
    expect(titleElement).toHaveClass('line-clamp-2');
  });

  it('keeps grid layout stable with mixed title lengths', () => {
    render(
      <MemoryRouter>
        <div className="grid grid-cols-3 gap-6" style={{ width: '900px' }}>
          <RecipeCard recipe={mockRecipeWithLongTitle} />
          <RecipeCard
            recipe={{
              ...mockRecipeWithLongTitle,
              id: '2',
              title: 'Short Title',
            }}
          />
          <RecipeCard
            recipe={{
              ...mockRecipeWithLongTitle,
              id: '3',
              title: 'Medium Length Recipe Title',
            }}
          />
        </div>
      </MemoryRouter>
    );

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(3);

    // All cards should be present and not overflow their containers
    links.forEach((link) => {
      expect(link).toBeInTheDocument();
      // Check that each card doesn't overflow horizontally
      expect(link.scrollWidth).toBeLessThanOrEqual(link.clientWidth + 1); // +1 for rounding
    });

    // Verify different titles are rendered correctly
    expect(screen.getByText(/extremely long recipe title/)).toBeInTheDocument();
    expect(screen.getByText('Short Title')).toBeInTheDocument();
    expect(screen.getByText('Medium Length Recipe Title')).toBeInTheDocument();
  });

  it('maintains semantic structure within card link', () => {
    render(
      <MemoryRouter>
        <RecipeCard recipe={mockRecipeWithLongTitle} />
      </MemoryRouter>
    );

    const linkElement = screen.getByRole('link');
    const withinLink = within(linkElement);

    // Verify semantic elements are properly nested within the link
    expect(withinLink.getByRole('heading', { level: 3 })).toBeInTheDocument();
    expect(
      withinLink.getByText('A test recipe description')
    ).toBeInTheDocument();
    expect(withinLink.getByText('Dinner')).toBeInTheDocument(); // Category badge
    expect(withinLink.getByText('Medium')).toBeInTheDocument(); // Difficulty
  });
});
