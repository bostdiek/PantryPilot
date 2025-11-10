import type { FC } from 'react';
import type { MealEntry } from '../types/MealPlan';
import type { Recipe } from '../types/Recipe';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Icon } from './ui/Icon';
import CheckIcon from './ui/icons/check.svg?react';
import ChefHatIcon from './ui/icons/chef-hat.svg?react';
import PencilIcon from './ui/icons/pencil.svg?react';
import RestaurantIcon from './ui/icons/restaurant.svg?react';

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

  // Determine icon for meal type
  const getMealIcon = () => {
    if (entry.isEatingOut) return RestaurantIcon;
    return ChefHatIcon;
  };

  const MealIcon = getMealIcon();

  return (
    <Card
      className={`overflow-hidden transition-shadow hover:shadow-md ${
        isToday 
          ? 'border-2 border-primary-400 bg-primary-50/40 shadow-sm' 
          : 'border border-gray-300 bg-white shadow-sm'
      }`}
    >
      <div className="flex items-center gap-4 p-4">
        {/* Recipe icon with better styling */}
        <div 
          className={`flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-xl ${
            entry.isEatingOut 
              ? 'bg-orange-100' 
              : entry.isLeftover 
                ? 'bg-yellow-100' 
                : 'bg-primary-100'
          }`}
        >
          <Icon 
            svg={MealIcon} 
            className={`h-8 w-8 ${
              entry.isEatingOut 
                ? 'text-orange-600' 
                : entry.isLeftover 
                  ? 'text-yellow-600' 
                  : 'text-primary-600'
            }`}
            title={entry.isEatingOut ? 'Restaurant' : 'Recipe'}
          />
        </div>

        {/* Content with improved typography */}
        <div className="min-w-0 flex-1">
          {hasRecipe && onRecipeClick ? (
            <button
              onClick={onRecipeClick}
              className="w-full text-left focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded-md transition-colors"
            >
              <h4 className="line-clamp-2 text-base font-semibold text-gray-900 hover:text-primary-700 leading-snug">
                {label}
              </h4>
            </button>
          ) : (
            <h4 className="line-clamp-2 text-base font-semibold text-gray-900 leading-snug">{label}</h4>
          )}
          
          {/* Meal type with icon-style badge */}
          <div className="mt-1 flex items-center gap-2">
            {entry.isEatingOut && (
              <span className="text-sm font-medium text-orange-700">Restaurant</span>
            )}
            {entry.isLeftover && (
              <span className="text-sm font-medium text-yellow-700">Leftovers</span>
            )}
            {hasRecipe && recipe.category && (
              <span className="text-sm font-medium text-gray-600 capitalize">
                {recipe.category}
              </span>
            )}
          </div>

          {/* Recipe timing info with better formatting */}
          {hasRecipe && recipe.total_time_minutes && (
            <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
              <span className="font-medium">{recipe.total_time_minutes} min</span>
              {recipe.difficulty && (
                <>
                  <span className="text-gray-300">•</span>
                  <span className="capitalize">{recipe.difficulty}</span>
                </>
              )}
            </div>
          )}

          {/* Cooked status with improved badge */}
          {entry.wasCooked && (
            <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-800">
              <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Cooked
              {entry.cookedAt && (
                <span className="text-green-700">
                  {new Date(entry.cookedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Actions with improved button styling */}
        <div className="flex flex-shrink-0 items-center gap-2">
          {!entry.wasCooked && onMarkCooked && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onMarkCooked}
              className="min-h-[48px] min-w-[48px] touch-manipulation rounded-lg border border-gray-200 bg-white p-0 hover:bg-green-50 hover:border-green-300 transition-colors"
              aria-label={`Mark ${label} as cooked`}
              title="Mark as cooked"
            >
              <Icon svg={CheckIcon} className="h-5 w-5 text-green-600" title="" />
            </Button>
          )}
          
          {onEdit && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onEdit}
              className="min-h-[48px] min-w-[48px] touch-manipulation rounded-lg border border-gray-200 bg-white p-0 hover:bg-blue-50 hover:border-blue-300 transition-colors"
              aria-label={`Edit ${label}`}
              title="Edit meal"
            >
              <Icon svg={PencilIcon} className="h-5 w-5 text-blue-600" title="" />
            </Button>
          )}

          {!hasRecipe && !entry.isEatingOut && !entry.isLeftover && onAddRecipe && (
            <Button
              variant="primary"
              size="sm"
              onClick={onAddRecipe}
              className="min-h-[48px] touch-manipulation whitespace-nowrap px-4 text-sm font-medium shadow-sm"
            >
              Add Recipe
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
};
