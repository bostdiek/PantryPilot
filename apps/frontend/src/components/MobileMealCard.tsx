import type { FC } from 'react';
import type { MealEntry } from '../types/MealPlan';
import type { Recipe } from '../types/Recipe';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Icon } from './ui/Icon';
import CheckIcon from './ui/icons/check.svg?react';
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
   * Whether this meal is for today
   */
  isToday?: boolean;

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
   * Callback when the meal should be removed
   */
  _onRemove?: () => void;

  /**
   * Callback when the recipe is clicked (for preview)
   */
  onRecipeClick?: () => void;
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
  isToday = false,
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
    <Card
      className={`p-3 ${isToday ? 'border-primary-300 bg-primary-50/30' : 'border-gray-200'}`}
    >
      <div className="flex items-start gap-3">
        {/* Recipe placeholder icon */}
        <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-lg bg-gray-100">
          <div className="flex h-full w-full items-center justify-center text-gray-400">
            <svg
              className="h-8 w-8"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
          </div>
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          {hasRecipe && onRecipeClick ? (
            <button
              onClick={onRecipeClick}
              className="w-full text-left focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 rounded-sm"
            >
              <h4 className="truncate font-medium text-gray-900 hover:text-primary-700">
                {label}
              </h4>
            </button>
          ) : (
            <h4 className="truncate font-medium text-gray-900">{label}</h4>
          )}
          
          {/* Meal type or metadata */}
          <p className="mt-0.5 text-sm text-gray-600">
            {entry.isEatingOut && 'Restaurant'}
            {entry.isLeftover && 'Leftovers from earlier'}
            {hasRecipe && recipe.category && (
              <span className="capitalize">{recipe.category}</span>
            )}
          </p>

          {/* Recipe timing info */}
          {hasRecipe && recipe.total_time_minutes && (
            <p className="mt-1 text-xs text-gray-500">
              {recipe.total_time_minutes} min total
              {recipe.difficulty && ` • ${recipe.difficulty}`}
            </p>
          )}

          {/* Cooked status */}
          {entry.wasCooked && (
            <span className="mt-2 inline-block rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">
              Cooked
              {entry.cookedAt && ` at ${new Date(entry.cookedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2">
          {!entry.wasCooked && onMarkCooked && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onMarkCooked}
              className="min-h-[48px] min-w-[48px] touch-manipulation p-0"
              aria-label={`Mark ${label} as cooked`}
              title="Mark as cooked"
            >
              <Icon svg={CheckIcon} className="h-5 w-5" title="" />
            </Button>
          )}
          
          {onEdit && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onEdit}
              className="min-h-[48px] min-w-[48px] touch-manipulation p-0"
              aria-label={`Edit ${label}`}
              title="Edit meal"
            >
              <Icon svg={PencilIcon} className="h-5 w-5" title="" />
            </Button>
          )}

          {!hasRecipe && !entry.isEatingOut && !entry.isLeftover && onAddRecipe && (
            <Button
              variant="outline"
              size="sm"
              onClick={onAddRecipe}
              className="min-h-[48px] touch-manipulation whitespace-nowrap px-3 text-xs"
            >
              Add Recipe
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
};
