import { Link } from 'react-router-dom';
import type { Recipe } from '../../types/Recipe';
import { Card } from '../ui/Card';

interface RecipeCardProps {
  recipe: Recipe;
  className?: string;
}

/**
 * Enhanced recipe card component for the recipes grid
 * Shows recipe details with hover effects and proper accessibility
 */
export function RecipeCard({ recipe, className = '' }: RecipeCardProps) {
  const totalTime =
    (recipe.prep_time_minutes ?? 0) + (recipe.cook_time_minutes ?? 0);

  // Format difficulty for display
  const formatDifficulty = (difficulty: string) => {
    return difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
  };

  // Format category for display
  const formatCategory = (category: string) => {
    return category.charAt(0).toUpperCase() + category.slice(1);
  };

  // Format serving info
  const formatServings = (min: number, max?: number) => {
    if (max && max !== min) {
      return `${min}-${max} servings`;
    }
    return `${min} serving${min !== 1 ? 's' : ''}`;
  };

  return (
    <Link to={`/recipes/${recipe.id}`} className={`group ${className}`}>
      <Card
        variant="elevated"
        className="h-full overflow-hidden p-0 transition-all duration-200 group-hover:scale-[1.02] hover:shadow-lg"
      >
        {/* Recipe content */}
        {/* min-w-0 allows long titles to wrap inside a flex parent and prevents overflow */}
        <div className="p-4 min-w-0">
          {/* Category badge at top */}
          <div className="mb-3 flex justify-end">
            <span className="inline-block rounded-full bg-orange-100 px-2 py-1 text-xs font-medium text-orange-700">
              {formatCategory(recipe.category)}
            </span>
          </div>
          {/* Title */}
          <h3 className="mb-2 line-clamp-2 text-lg font-semibold text-gray-900 transition-colors group-hover:text-blue-600">
            {recipe.title}
          </h3>

          {/* Description */}
          {recipe.description && (
            <p className="mb-3 line-clamp-2 text-sm text-gray-600">
              {recipe.description}
            </p>
          )}

          {/* Recipe details */}
          <div className="space-y-2 text-xs text-gray-500">
            {/* Time and difficulty */}
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1">
                ⏱️ {totalTime} mins
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${
                  recipe.difficulty === 'easy'
                    ? 'bg-green-100 text-green-700'
                    : recipe.difficulty === 'medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                }`}
              >
                {formatDifficulty(recipe.difficulty)}
              </span>
            </div>

            {/* Servings */}
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1">
                👥 {formatServings(recipe.serving_min, recipe.serving_max)}
              </span>
              {recipe.oven_temperature_f && (
                <span className="flex items-center gap-1">
                  🔥 {recipe.oven_temperature_f}°F
                </span>
              )}
            </div>
          </div>

          {/* Ingredients preview */}
          {recipe.ingredients.length > 0 && (
            <div className="mt-3 border-t border-gray-100 pt-3">
              <div className="text-xs text-gray-500">
                <span className="font-medium">
                  {recipe.ingredients.length} ingredients:
                </span>
                <span className="ml-1">
                  {recipe.ingredients
                    .slice(0, 3)
                    .map((ing) => ing.name)
                    .join(', ')}
                  {recipe.ingredients.length > 3 && '...'}
                </span>
              </div>
            </div>
          )}

          {/* Ethnicity tag if available */}
          {recipe.ethnicity && (
            <div className="mt-2">
              <span className="inline-block rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                {recipe.ethnicity}
              </span>
            </div>
          )}
        </div>
      </Card>
    </Link>
  );
}
