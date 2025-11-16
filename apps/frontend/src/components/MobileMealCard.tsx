import type { FC } from 'react';
import type { MealEntry } from '../types/MealPlan';
import type { Recipe } from '../types/Recipe';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Icon } from './ui/Icon';
import PencilIcon from './ui/icons/pencil.svg?react';

export interface MobileMealCardProps {
  /**
   * The meal entry to display
   */
  entry: MealEntry;

  /**
   * Recipe data for the meal entry (if it has a recipe)
   */
  recipe?: Recipe | null;

  /**
   * Callback when the meal should be edited
   */
  onEdit?: () => void;

  /**
   * Callback when a recipe should be added to this meal
   */
  onAddRecipe?: () => void;

  /**
   * Callback when the meal should be marked as cooked
   */
  onMarkCooked?: () => void;

  /**
   * Callback when the recipe is clicked (for preview)
   */
  onRecipeClick?: () => void;

  /**
   * Callback when the meal should be removed (not yet implemented in UI)
   */
  _onRemove?: () => void;
}

/**
 * Mobile-optimized meal card with touch-friendly interactions
 *
 * Features:
 * - Minimum 48px touch targets for all interactive elements
 * - Recipe image preview
 * - Clear meal type and timing information
 * - Touch-optimized action buttons
 */
export const MobileMealCard: FC<MobileMealCardProps> = ({
  entry,
  recipe,
  onEdit,
  onAddRecipe,
  onMarkCooked,
  onRecipeClick,
}) => {
  // Determine label based on entry type
  const getLabel = () => {
    if (entry.isEatingOut) return 'Eating out';
    if (entry.isLeftover) return 'Leftovers';
    if (recipe) return recipe.title;
    return 'No recipe selected';
  };

  const label = getLabel();
  const hasRecipe = !!entry.recipeId && !!recipe;

  return (
    <Card className="border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <div className="p-4">
        {/* Recipe name - prominent and clear */}
        <div className="mb-3">
          {hasRecipe && onRecipeClick ? (
            <button
              onClick={onRecipeClick}
              className="group w-full rounded-md text-left transition-colors focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none"
              aria-label={`View ${label} recipe preview`}
            >
              <h3 className="line-clamp-2 text-lg leading-tight font-semibold text-gray-900 group-hover:text-blue-700">
                {label}
              </h3>
            </button>
          ) : (
            <h3 className="line-clamp-2 text-lg leading-tight font-semibold text-gray-900">
              {label}
            </h3>
          )}

          {/* Recipe metadata - show time and difficulty */}
          {hasRecipe && (recipe.total_time_minutes || recipe.difficulty) && (
            <div className="mt-1 text-sm text-gray-600">
              {recipe.total_time_minutes ? (
                <>
                  {recipe.total_time_minutes} min
                  {recipe.difficulty && (
                    <span className="ml-2 text-gray-500 capitalize">
                      • {recipe.difficulty}
                    </span>
                  )}
                </>
              ) : recipe.difficulty ? (
                <span className="text-gray-500 capitalize">
                  {recipe.difficulty}
                </span>
              ) : null}
            </div>
          )}
        </div>

        {/* Status and actions row */}
        <div className="flex items-center justify-between">
          {/* Cooking status */}
          <div className="flex items-center gap-3">
            {entry.wasCooked ? (
              <span className="inline-flex items-center gap-1.5 rounded-md bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
                <svg
                  className="h-4 w-4"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                Cooked
              </span>
            ) : (
              <span className="text-sm text-gray-500">Not cooked yet</span>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {!entry.wasCooked && onMarkCooked && (
              <Button
                variant="outline"
                size="sm"
                onClick={onMarkCooked}
                className="px-3 py-1 text-sm"
                aria-label={`Mark ${label} as cooked`}
              >
                Mark Cooked
              </Button>
            )}

            {onEdit && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onEdit}
                className="p-2"
                aria-label={`Edit ${label}`}
                title="Edit"
              >
                <Icon
                  svg={PencilIcon}
                  className="h-4 w-4 text-gray-600"
                  aria-hidden="true"
                />
              </Button>
            )}
          </div>
        </div>

        {/* Add recipe button for empty entries */}
        {!hasRecipe &&
          !entry.isEatingOut &&
          !entry.isLeftover &&
          onAddRecipe && (
            <div className="mt-3 border-t border-gray-100 pt-3">
              <Button
                variant="primary"
                size="sm"
                onClick={onAddRecipe}
                className="w-full"
              >
                Add Recipe
              </Button>
            </div>
          )}
      </div>
    </Card>
  );
};
