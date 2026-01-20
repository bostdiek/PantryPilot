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

describe('RecipeCardBlock draft link handling', () => {
  test('renders "Add Recipe" button for draft deep-link', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'Suggested Pasta Recipe',
      subtitle: 'From Nibble AI',
      image_url: null,
      href: '/recipes/new?ai=1&draftId=abc123&token=xyz789',
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    expect(screen.getByText('Add Recipe')).toBeInTheDocument();
    expect(screen.queryByText('View Recipe')).not.toBeInTheDocument();
  });

  test('renders "View Recipe" button for external links', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'External Recipe',
      subtitle: null,
      image_url: null,
      href: 'https://recipes.example.com/pasta-recipe',
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    expect(screen.getByText('View Recipe')).toBeInTheDocument();
    expect(screen.queryByText('Add Recipe')).not.toBeInTheDocument();
  });

  test('uses React Router Link for draft links (internal navigation)', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'Draft Recipe',
      subtitle: null,
      image_url: null,
      href: '/recipes/new?ai=1&draftId=draft-123&token=secret',
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    const link = screen.getByRole('link');
    // React Router Link creates internal href
    expect(link).toHaveAttribute(
      'href',
      '/recipes/new?ai=1&draftId=draft-123&token=secret'
    );
    // Should not have target="_blank" (external link attribute)
    expect(link).not.toHaveAttribute('target');
  });

  test('uses anchor tag with target="_blank" for external links', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'External Site Recipe',
      subtitle: null,
      image_url: null,
      href: 'https://allrecipes.com/recipe/123',
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', 'https://allrecipes.com/recipe/123');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  test('draft link with additional query params still shows Add Recipe', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'Complex Draft URL',
      subtitle: null,
      image_url: null,
      href: '/recipes/new?ai=1&draftId=id&token=tok&source=chat',
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    expect(screen.getByText('Add Recipe')).toBeInTheDocument();
  });

  test('does not show action button when recipe_id is provided', () => {
    // When recipe_id is provided, it links directly to recipe detail
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: 'existing-recipe-123',
      title: 'Saved Recipe',
      subtitle: null,
      image_url: null,
      href: null,
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    expect(screen.queryByText('Add Recipe')).not.toBeInTheDocument();
    expect(screen.queryByText('View Recipe')).not.toBeInTheDocument();
    // Still has a link to the recipe detail page
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/recipes/existing-recipe-123');
  });

  test('Add Recipe button has correct accessibility label', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'Accessible Draft',
      subtitle: null,
      image_url: null,
      href: '/recipes/new?ai=1&draftId=123&token=abc',
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    const button = screen.getByLabelText('Add this recipe to your collection');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Add Recipe');
  });

  test('View Recipe button has correct accessibility label', () => {
    const block: RecipeCardBlockType = {
      type: 'recipe_card',
      recipe_id: null,
      title: 'External View',
      subtitle: null,
      image_url: null,
      href: 'https://example.com/recipe',
    };

    renderWithRouter(<RecipeCardBlock block={block} />);

    const button = screen.getByLabelText('View recipe on external site');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('View Recipe');
  });
});
