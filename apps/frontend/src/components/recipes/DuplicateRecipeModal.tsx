import { useState, type FC } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Recipe } from '../../types/Recipe';
import { Button } from '../ui/Button';
import { Dialog } from '../ui/Dialog';
import AlertTriangleIcon from '../ui/icons/alert-triangle.svg?react';

/**
 * Similar recipe match with similarity percentage
 */
export interface SimilarRecipeMatch {
  recipe: Recipe;
  similarity: number;
}

export interface DuplicateRecipeModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Function to close the modal */
  onClose: () => void;
  /** Type of duplicate detected */
  duplicateType: 'exact' | 'similar';
  /** The existing recipe for exact matches */
  existingRecipe?: Recipe;
  /** List of similar recipes for fuzzy matches */
  similarRecipes?: SimilarRecipeMatch[];
  /** Callback when user chooses to view the existing recipe */
  onViewExisting: (recipeId: string) => void;
  /** Callback when user chooses to create the recipe anyway */
  onCreateAnyway: () => void;
  /** Whether the create anyway action is loading */
  isCreatingAnyway?: boolean;
}

/**
 * Modal displayed when a duplicate or similar recipe is detected during creation.
 * Gives users the option to view the existing recipe, create anyway, or cancel.
 */
export const DuplicateRecipeModal: FC<DuplicateRecipeModalProps> = ({
  isOpen,
  onClose,
  duplicateType,
  existingRecipe,
  similarRecipes = [],
  onViewExisting,
  onCreateAnyway,
  isCreatingAnyway = false,
}) => {
  const navigate = useNavigate();
  const [selectedRecipeId, setSelectedRecipeId] = useState<string | null>(null);

  const handleViewExisting = (recipeId: string) => {
    onViewExisting(recipeId);
    navigate(`/recipes/${recipeId}`);
    onClose();
  };

  const handleCreateAnyway = () => {
    onCreateAnyway();
  };

  const handleClose = () => {
    if (!isCreatingAnyway) {
      setSelectedRecipeId(null);
      onClose();
    }
  };

  const isExactMatch = duplicateType === 'exact';
  const title = isExactMatch
    ? 'Recipe Already Exists'
    : 'Similar Recipes Found';

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleClose}
      title={
        <div className="flex items-center gap-2">
          <AlertTriangleIcon className="h-6 w-6 text-amber-500" />
          <span>{title}</span>
        </div>
      }
      size="md"
      static={isCreatingAnyway}
    >
      <div className="space-y-4">
        {/* Exact match content */}
        {isExactMatch && existingRecipe && (
          <div className="space-y-3">
            <p className="text-gray-600">
              A recipe with this name already exists in your collection:
            </p>
            <RecipePreviewCard
              recipe={existingRecipe}
              isSelected={selectedRecipeId === existingRecipe.id}
              onSelect={() => setSelectedRecipeId(existingRecipe.id)}
            />
          </div>
        )}

        {/* Similar matches content */}
        {!isExactMatch && similarRecipes.length > 0 && (
          <div className="space-y-3">
            <p className="text-gray-600">
              We found similar recipes in your collection. Would you like to
              view one of these instead?
            </p>
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {similarRecipes.map(({ recipe, similarity }) => (
                <RecipePreviewCard
                  key={recipe.id}
                  recipe={recipe}
                  similarity={similarity}
                  isSelected={selectedRecipeId === recipe.id}
                  onSelect={() => setSelectedRecipeId(recipe.id)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-col-reverse gap-2 pt-4 sm:flex-row sm:justify-end">
          <Button
            variant="ghost"
            onClick={handleClose}
            disabled={isCreatingAnyway}
          >
            Cancel
          </Button>
          <Button
            variant="outline"
            onClick={handleCreateAnyway}
            disabled={isCreatingAnyway}
            loading={isCreatingAnyway}
          >
            Create Anyway
          </Button>
          {selectedRecipeId ? (
            <Button
              variant="primary"
              onClick={() => handleViewExisting(selectedRecipeId)}
              disabled={isCreatingAnyway}
            >
              View Selected
            </Button>
          ) : existingRecipe ? (
            <Button
              variant="primary"
              onClick={() => handleViewExisting(existingRecipe.id)}
              disabled={isCreatingAnyway}
            >
              View Existing
            </Button>
          ) : null}
        </div>
      </div>
    </Dialog>
  );
};

/**
 * Recipe preview card for displaying in the duplicate modal
 */
interface RecipePreviewCardProps {
  recipe: Recipe;
  similarity?: number;
  isSelected?: boolean;
  onSelect?: () => void;
}

const RecipePreviewCard: FC<RecipePreviewCardProps> = ({
  recipe,
  similarity,
  isSelected = false,
  onSelect,
}) => {
  const totalTime = recipe.prep_time_minutes + recipe.cook_time_minutes;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border p-3 text-left transition-colors ${
        isSelected
          ? 'border-green-500 bg-green-50 ring-1 ring-green-500'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <h4 className="truncate font-medium text-gray-900">{recipe.title}</h4>
          {recipe.description && (
            <p className="mt-1 line-clamp-2 text-sm text-gray-500">
              {recipe.description}
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
            {totalTime > 0 && <span>{totalTime} min</span>}
            {recipe.difficulty && (
              <>
                <span>•</span>
                <span className="capitalize">{recipe.difficulty}</span>
              </>
            )}
            {recipe.category && (
              <>
                <span>•</span>
                <span className="capitalize">{recipe.category}</span>
              </>
            )}
          </div>
        </div>
        {similarity !== undefined && (
          <div className="ml-3 flex-shrink-0">
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800">
              {Math.round(similarity * 100)}% match
            </span>
          </div>
        )}
      </div>
    </button>
  );
};

DuplicateRecipeModal.displayName = 'DuplicateRecipeModal';
