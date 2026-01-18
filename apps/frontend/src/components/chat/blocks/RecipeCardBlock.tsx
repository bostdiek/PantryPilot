/**
 * RecipeCardBlock component for rendering recipe preview cards.
 *
 * Displays a compact recipe card with optional image, title,
 * subtitle, and deep link to the recipe detail page.
 */

import { ChefHat } from 'lucide-react';
import { Link } from 'react-router-dom';

import type { RecipeCardBlock as RecipeCardBlockType } from '../../../types/Chat';

interface RecipeCardBlockProps {
  block: RecipeCardBlockType;
}

/**
 * Renders a recipe card block with optional image and link.
 */
export function RecipeCardBlock({ block }: RecipeCardBlockProps) {
  const content = (
    <div className="group hover:border-primary-300 hover:bg-primary-50 my-1 flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 transition-colors">
      {/* Recipe image or placeholder */}
      <div className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-md bg-gray-100">
        {block.image_url ? (
          <img
            src={block.image_url}
            alt={block.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <ChefHat className="h-6 w-6 text-gray-400" />
          </div>
        )}
      </div>

      {/* Recipe info */}
      <div className="min-w-0 flex-1">
        <div className="group-hover:text-primary-700 truncate font-medium text-gray-900">
          {block.title}
        </div>
        {block.subtitle && (
          <div className="truncate text-xs text-gray-500">{block.subtitle}</div>
        )}
      </div>
    </div>
  );

  // If we have a recipe_id or href, wrap in a link
  if (block.recipe_id) {
    return (
      <Link to={`/recipes/${block.recipe_id}`} className="block">
        {content}
      </Link>
    );
  }

  if (block.href) {
    // Check if it's an internal link
    try {
      const url = new URL(block.href, window.location.origin);
      if (url.origin === window.location.origin) {
        return (
          <Link to={url.pathname + url.search} className="block">
            {content}
          </Link>
        );
      }
    } catch {
      // Fall through to external link
    }

    return (
      <a
        href={block.href}
        target="_blank"
        rel="noopener noreferrer"
        className="block"
      >
        {content}
      </a>
    );
  }

  // No link, just render the card
  return content;
}
