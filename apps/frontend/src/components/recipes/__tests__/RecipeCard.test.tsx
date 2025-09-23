import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { RecipeCard } from '../RecipeCard';
import type { Recipe } from '../../../types/Recipe';

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

const mockRecipe: Recipe = {
  id: '1',
  title: 'Test Recipe',
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
    {
      id: '2',
      name: 'Olive Oil',
      quantity_value: 2,
      quantity_unit: 'tbsp',
      prep: null,
      is_optional: false,
    },
  ],
  instructions: ['Step 1', 'Step 2'],
  user_notes: null,
  created_at: new Date('2024-01-01'),
  updated_at: new Date('2024-01-01'),
};

describe('RecipeCard', () => {
  it('renders recipe information without image placeholder', () => {
    render(
      <MemoryRouter>
        <RecipeCard recipe={mockRecipe} />
      </MemoryRouter>
    );

    // Verify recipe title is rendered
    expect(screen.getByText('Test Recipe')).toBeInTheDocument();

    // Verify description is rendered
    expect(screen.getByText('A test recipe description')).toBeInTheDocument();

    // Verify category badge is rendered
    expect(screen.getByText('Dinner')).toBeInTheDocument();

    // Verify timing information is rendered
    expect(screen.getByText('⏱️ 35 mins')).toBeInTheDocument();

    // Verify difficulty is rendered
    expect(screen.getByText('Medium')).toBeInTheDocument();

    // Verify ingredients preview is rendered
    expect(screen.getByText('2 ingredients:')).toBeInTheDocument();
    expect(screen.getByText('Tomatoes, Olive Oil')).toBeInTheDocument();
  });

  it('renders without gradient background placeholder', () => {
    const { container } = render(
      <MemoryRouter>
        <RecipeCard recipe={mockRecipe} />
      </MemoryRouter>
    );

    // Verify there's no gradient background element
    const gradientElement = container.querySelector('.bg-gradient-to-br');
    expect(gradientElement).toBeNull();

    // Verify there's no h-48 height element (the old image placeholder)
    const largeHeightElement = container.querySelector('.h-48');
    expect(largeHeightElement).toBeNull();
  });

  it('displays category badge at top of content area', () => {
    render(
      <MemoryRouter>
        <RecipeCard recipe={mockRecipe} />
      </MemoryRouter>
    );

    const categoryBadge = screen.getByText('Dinner');
    expect(categoryBadge).toBeInTheDocument();

    // Verify it has the proper styling classes for top positioning
    expect(categoryBadge.closest('.mb-3')).toBeInTheDocument();
  });

  it('renders preview button when enablePreview is true', async () => {
    const mockOnPreview = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RecipeCard 
          recipe={mockRecipe} 
          enablePreview={true}
          onPreview={mockOnPreview}
        />
      </MemoryRouter>
    );

    // Preview button should be present
    const previewButton = screen.getByRole('button', { name: /preview test recipe/i });
    expect(previewButton).toBeInTheDocument();

    // Click preview button and verify callback
    await user.click(previewButton);
    expect(mockOnPreview).toHaveBeenCalledWith(mockRecipe);
  });

  it('does not render preview button when enablePreview is false or undefined', () => {
    render(
      <MemoryRouter>
        <RecipeCard recipe={mockRecipe} />
      </MemoryRouter>
    );

    // Preview button should not be present
    const previewButton = screen.queryByRole('button', { name: /preview/i });
    expect(previewButton).not.toBeInTheDocument();
  });
});
