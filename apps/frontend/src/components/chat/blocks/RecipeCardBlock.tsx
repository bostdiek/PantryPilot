/**
 * RecipeCardBlock component for rendering recipe preview cards.
 *
 * Displays a compact recipe card with optional image, title,
 * subtitle, and deep link to the recipe detail page.
 *
 * For AI-suggested recipes (with source_url):
 * - Clicking the card body opens the external source URL
 * - Clicking "Add Recipe" navigates to the draft approval page
 *
 * For saved recipes (with recipe_id):
 * - Clicking anywhere navigates to the recipe detail page
 */

import { ChefHat, ExternalLink, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';

import type { RecipeCardBlock as RecipeCardBlockType } from '../../../types/Chat';

interface RecipeCardBlockProps {
  block: RecipeCardBlockType;
}

/**
 * Check if a URL path is a draft deep-link for AI recipe approval.
 * Draft links are internal navigation to /recipes/new with ai=1 parameter.
 */
function isDraftLink(href: string): boolean {
  // Handle both absolute URLs with origin and relative paths
  try {
    const url = new URL(href, window.location.origin);
    return (
      url.pathname === '/recipes/new' && url.searchParams.get('ai') === '1'
    );
  } catch {
    // For malformed URLs, check as simple string
    return href.startsWith('/recipes/new?ai=1');
  }
}

/**
 * Renders a recipe card block with optional image and link.
 *
 * For AI suggestions: card body links to source, button links to add page.
 * For saved recipes: entire card links to recipe detail page.
 */
export function RecipeCardBlock({ block }: RecipeCardBlockProps) {
  const hasDraftLink = block.href ? isDraftLink(block.href) : false;
  const hasSourceUrl = !!block.source_url;

  // For AI suggestions with source URL: split clickable areas
  if (hasDraftLink && hasSourceUrl) {
    return (
      <div className="group my-1 flex max-w-full items-center gap-3 overflow-hidden rounded-lg border border-gray-200 bg-white p-3 transition-colors hover:border-blue-300 hover:bg-blue-50">
        {/* Card body links to external source */}
        <a
          href={block.source_url!}
          target="_blank"
          rel="noopener noreferrer"
          className="flex min-w-0 flex-1 items-center gap-3 overflow-hidden"
          aria-label={`View ${block.title} on external site`}
        >
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
          <div className="min-w-0 flex-1 overflow-hidden">
            <div className="truncate font-medium text-blue-700 group-hover:text-blue-800 group-hover:underline">
              {block.title}
              <ExternalLink
                className="ml-1 inline h-3 w-3"
                aria-hidden="true"
              />
            </div>
            {block.subtitle && (
              <div className="truncate text-xs text-gray-500">
                {block.subtitle}
              </div>
            )}
          </div>
        </a>

        {/* Add Recipe button links to internal draft page */}
        {(() => {
          const normalizedPath = block.href!.startsWith('/')
            ? block.href!
            : (() => {
                const url = new URL(block.href!, window.location.origin);
                return url.pathname + url.search;
              })();
          return (
            <Link
              to={normalizedPath}
              className="flex-shrink-0"
              aria-label="Add this recipe to your collection"
            >
              <span className="inline-flex items-center gap-1 rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-green-700">
                <Plus className="h-4 w-4" aria-hidden="true" />
                Add Recipe
              </span>
            </Link>
          );
        })()}
      </div>
    );
  }

  // Standard card content for other cases
  const content = (
    <div className="group hover:border-primary-300 hover:bg-primary-50 my-1 flex max-w-full items-center gap-3 overflow-hidden rounded-lg border border-gray-200 bg-white p-3 transition-colors">
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
      <div className="min-w-0 flex-1 overflow-hidden">
        <div className="group-hover:text-primary-700 truncate font-medium text-gray-900">
          {block.title}
        </div>
        {block.subtitle && (
          <div className="truncate text-xs text-gray-500">{block.subtitle}</div>
        )}
      </div>

      {/* Action button for links with href (not recipe_id direct links) */}
      {block.href && !block.recipe_id && (
        <div className="flex-shrink-0">
          {hasDraftLink ? (
            <span className="inline-flex items-center gap-1 rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white transition-colors group-hover:bg-green-700">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Recipe
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition-colors group-hover:bg-blue-700">
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              View Recipe
            </span>
          )}
        </div>
      )}
    </div>
  );

  // If we have a recipe_id, link to recipe detail page
  if (block.recipe_id) {
    return (
      <Link to={`/recipes/${block.recipe_id}`} className="block">
        {content}
      </Link>
    );
  }

  if (block.href) {
    // Check if it's an internal link (same origin or relative path)
    try {
      const url = new URL(block.href, window.location.origin);
      if (url.origin === window.location.origin) {
        // Internal navigation (includes draft links)
        const ariaLabel = hasDraftLink
          ? 'Add this recipe to your collection'
          : `View ${block.title}`;
        return (
          <Link
            to={url.pathname + url.search}
            className="block"
            aria-label={ariaLabel}
          >
            {content}
          </Link>
        );
      }
    } catch {
      // Fall through to external link
    }

    // External link opens in new tab
    return (
      <a
        href={block.href}
        target="_blank"
        rel="noopener noreferrer"
        className="block"
        aria-label={`View ${block.title} on external site`}
      >
        {content}
      </a>
    );
  }

  // No link, just render the card
  return content;
}
