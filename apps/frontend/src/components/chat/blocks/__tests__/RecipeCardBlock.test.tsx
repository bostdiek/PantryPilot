/**
 * @file RecipeCardBlock.test.tsx
 * Tests for the RecipeCardBlock component that renders recipe preview cards.
 */

import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, test } from 'vitest';

import type { RecipeCardBlock as RecipeCardBlockType } from '../../../../types/Chat';
import { RecipeCardBlock } from '../RecipeCardBlock';

// Wrapper to provide router context
function renderWithRouter(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('RecipeCardBlock', () => {
  test('renders recipe title', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: '123',
      title: 'Spaghetti Carbonara',
      subtitle: null,
      image_url: null,
      href: null,
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    expect(screen.getByText('Spaghetti Carbonara')).toBeInTheDocument();
  });

  test('renders recipe with subtitle', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: '123',
      title: 'Pasta Dish',
      subtitle: '30 min • Easy',
      image_url: null,
      href: null,
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    expect(screen.getByText('Pasta Dish')).toBeInTheDocument();
    expect(screen.getByText('30 min • Easy')).toBeInTheDocument();
  });

  test('renders recipe image when provided', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: '123',
      title: 'Pasta',
      subtitle: null,
      image_url: 'https://example.com/pasta.jpg',
      href: null,
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    const img = screen.getByRole('img', { name: 'Pasta' });
    expect(img).toHaveAttribute('src', 'https://example.com/pasta.jpg');
  });

  test('renders placeholder icon when no image', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: '123',
      title: 'Recipe Without Image',
      subtitle: null,
      image_url: null,
      href: null,
    };

    const { container } = renderWithRouter(<RecipeCardBlock block={block} />);

    // Should render ChefHat icon (SVG)
    const svgIcon = container.querySelector('svg');
    expect(svgIcon).toBeInTheDocument();
  });

  test('links to recipe detail page when recipe_id provided', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: 'abc-123',
      title: 'Linked Recipe',
      subtitle: null,
      image_url: null,
      href: null,
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/recipes/abc-123');
  });

  test('renders as link when href provided without recipe_id', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'External Recipe',
      subtitle: null,
      image_url: null,
      href: 'https://recipes.example.com/dish',
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', 'https://recipes.example.com/dish');
  });

  test('renders without link when no recipe_id or href', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'Static Recipe Card',
      subtitle: 'No link available',
      image_url: null,
      href: null,
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    expect(screen.getByText('Static Recipe Card')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  test('applies hover styles', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: '123',
      title: 'Hover Test Recipe',
      subtitle: null,
      image_url: null,
      href: null,
    };

    const { container } = renderWithRouter(<RecipeCardBlock block={block} />);

    const card = container.querySelector('.group');
    expect(card).toBeInTheDocument();
  });
});
