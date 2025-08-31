import { Dialog as HeadlessDialog, Transition } from '@headlessui/react';
import clsx from 'clsx';
import { Fragment, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/Button';
import type { Recipe } from '../types/Recipe';

export interface RecipeQuickPreviewProps {
  /**
   * Whether the preview is open
   */
  isOpen: boolean;

  /**
   * Function to close the preview
   */
  onClose: () => void;

  /**
   * Recipe to preview
   */
  recipe: Recipe | null;

  /**
   * Date context for navigation back to meal plan
   */
  dateContext?: string;

  /**
   * Function to remove recipe from the meal plan day
   */
  onRemoveFromDay?: () => void;
}

/**
 * RecipeQuickPreview component that shows a modal on desktop and bottom sheet on mobile
 * 
 * Displays recipe title, image placeholder, key metadata, first 5 ingredients,
 * and action buttons (View Full, Edit, Remove from day).
 */
export function RecipeQuickPreview({
  isOpen,
  onClose,
  recipe,
  dateContext,
  onRemoveFromDay,
}: RecipeQuickPreviewProps) {
  const navigate = useNavigate();

  // Close on Escape key - only register once
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        event.preventDefault();
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  if (!recipe) {
    return null;
  }

  const handleViewFull = () => {
    const queryParams = new URLSearchParams();
    if (dateContext) {
      queryParams.set('from', 'mealplan');
      queryParams.set('d', dateContext);
    }
    const searchString = queryParams.toString();
    const url = `/recipes/${recipe.id}${searchString ? `?${searchString}` : ''}`;
    navigate(url);
    onClose();
  };

  const handleEdit = () => {
    navigate(`/recipes/${recipe.id}/edit`);
    onClose();
  };

  const handleRemove = () => {
    if (onRemoveFromDay) {
      onRemoveFromDay();
    }
    // Don't call onClose() here - let the parent handle it after the async operation
  };

  const firstFiveIngredients = recipe.ingredients?.slice(0, 5) || [];
  const hasMoreIngredients = (recipe.ingredients?.length || 0) > 5;

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <HeadlessDialog
        as="div"
        className="relative z-50"
        onClose={onClose}
      >
        {/* Background overlay */}
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div
            className="fixed inset-0 bg-black/30 backdrop-blur-sm"
            aria-hidden="true"
          />
        </Transition.Child>

        {/* Mobile bottom sheet and desktop modal */}
        <div className="fixed inset-0 overflow-y-auto">
          {/* Desktop modal positioning */}
          <div className="hidden md:flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <HeadlessDialog.Panel
                className="w-full max-w-lg transform overflow-hidden rounded-lg bg-white text-left align-middle shadow-xl transition-all"
              >
                <RecipePreviewContent
                  recipe={recipe}
                  firstFiveIngredients={firstFiveIngredients}
                  hasMoreIngredients={hasMoreIngredients}
                  onViewFull={handleViewFull}
                  onEdit={handleEdit}
                  onRemove={onRemoveFromDay ? handleRemove : undefined}
                  onClose={onClose}
                />
              </HeadlessDialog.Panel>
            </Transition.Child>
          </div>

          {/* Mobile bottom sheet positioning */}
          <div className="md:hidden flex min-h-full items-end justify-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-full"
              enterTo="opacity-100 translate-y-0"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0"
              leaveTo="opacity-0 translate-y-full"
            >
              <HeadlessDialog.Panel
                className="w-full max-h-[85vh] transform overflow-hidden rounded-t-lg bg-white text-left align-middle shadow-xl transition-all"
              >
                <RecipePreviewContent
                  recipe={recipe}
                  firstFiveIngredients={firstFiveIngredients}
                  hasMoreIngredients={hasMoreIngredients}
                  onViewFull={handleViewFull}
                  onEdit={handleEdit}
                  onRemove={onRemoveFromDay ? handleRemove : undefined}
                  onClose={onClose}
                  isMobile
                />
              </HeadlessDialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </HeadlessDialog>
    </Transition>
  );
}

interface RecipePreviewContentProps {
  recipe: Recipe;
  firstFiveIngredients: Recipe['ingredients'];
  hasMoreIngredients: boolean;
  onViewFull: () => void;
  onEdit: () => void;
  onRemove?: () => void;
  onClose: () => void;
  isMobile?: boolean;
}

function RecipePreviewContent({
  recipe,
  firstFiveIngredients,
  hasMoreIngredients,
  onViewFull,
  onEdit,
  onRemove,
  onClose,
  isMobile = false,
}: RecipePreviewContentProps) {
  return (
    <div className={clsx('p-6', isMobile && 'max-h-[85vh] overflow-y-auto')}>
      {/* Mobile handle bar */}
      {isMobile && (
        <div className="flex justify-center pb-4">
          <div className="w-10 h-1 bg-gray-300 rounded-full" />
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <HeadlessDialog.Title
          as="h3"
          className="text-lg leading-6 font-semibold text-gray-900 pr-4"
        >
          {recipe.title}
        </HeadlessDialog.Title>
        {!isMobile && (
          <button
            onClick={onClose}
            className="flex-shrink-0 rounded-md text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Close preview"
          >
            <span className="sr-only">Close</span>
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Recipe description */}
      {recipe.description && (
        <p className="text-sm text-gray-600 mb-4 leading-relaxed">
          {recipe.description}
        </p>
      )}

      {/* Image placeholder */}
      <div className="w-full h-32 bg-gray-100 rounded-lg flex items-center justify-center mb-4">
        <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>

      {/* Key metadata */}
      <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
        <div className="text-center">
          <div className="font-medium text-gray-900">{recipe.total_time_minutes}</div>
          <div className="text-gray-500">minutes</div>
        </div>
        <div className="text-center">
          <div className="font-medium text-gray-900 capitalize">{recipe.difficulty}</div>
          <div className="text-gray-500">difficulty</div>
        </div>
        <div className="text-center">
          <div className="font-medium text-gray-900">
            {recipe.serving_max ? `${recipe.serving_min}-${recipe.serving_max}` : recipe.serving_min}
          </div>
          <div className="text-gray-500">servings</div>
        </div>
      </div>

      {/* First 5 ingredients */}
      <div className="mb-6">
        <h4 className="font-medium text-gray-900 mb-3">Ingredients</h4>
        <ul className="space-y-2">
          {firstFiveIngredients.map((ingredient, index) => (
            <li key={ingredient.id || index} className="text-sm text-gray-700 flex">
              <span className="font-medium w-16 flex-shrink-0">
                {ingredient.quantity_value || ''} {ingredient.quantity_unit || ''}
              </span>
              <span>{ingredient.name}</span>
            </li>
          ))}
        </ul>
        {hasMoreIngredients && (
          <p className="text-sm text-gray-500 mt-2">
            +{recipe.ingredients.length - 5} more ingredients
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 pt-4 border-t">
        <Button
          variant="primary"
          onClick={onViewFull}
          className="flex-1"
        >
          View Full Recipe
        </Button>
        <Button
          variant="outline"
          onClick={onEdit}
          className="flex-1"
        >
          Edit
        </Button>
        {onRemove && (
          <Button
            variant="danger"
            onClick={onRemove}
            className="flex-1"
          >
            Remove from Day
          </Button>
        )}
      </div>
    </div>
  );
}