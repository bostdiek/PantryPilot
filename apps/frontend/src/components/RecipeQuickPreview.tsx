import {
  DialogPanel,
  DialogTitle,
  Dialog as HeadlessDialog,
  Transition,
  TransitionChild,
} from '@headlessui/react';
import clsx from 'clsx';
import { Fragment, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Recipe } from '../types/Recipe';
import { Button } from './ui/Button';

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

  // Centralized close handler
  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  // Close on Escape key - only register once
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        event.preventDefault();
        handleClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, handleClose]);

  if (!recipe) {
    return null;
  }

  const buildViewFullUrl = () => {
    const queryParams = new URLSearchParams();
    if (dateContext) {
      queryParams.set('from', 'mealplan');
      queryParams.set('d', dateContext);
    }
    const searchString = queryParams.toString();
    return `/recipes/${recipe.id}${searchString ? `?${searchString}` : ''}`;
  };

  const viewFullUrl = buildViewFullUrl();

  const handleViewFullClick = () => {
    const url = viewFullUrl;
    // Intentionally do not call onClose; routing will unmount this dialog
    navigate(url);
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
        onClose={() => {}} // Disable automatic close, handle manually
      >
        {/* Background overlay */}
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
            onClick={handleClose}
            aria-hidden="true"
          />
        </TransitionChild>

        {/* Mobile bottom sheet and desktop modal */}
        <div className="fixed inset-0 z-50 overflow-y-auto">
          {/* Desktop modal positioning */}
          <div className="hidden min-h-full items-center justify-center p-4 text-center md:flex">
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <DialogPanel className="relative z-50 w-full max-w-lg transform overflow-hidden rounded-lg bg-white text-left align-middle shadow-xl transition-all">
                <RecipePreviewContent
                  recipe={recipe}
                  firstFiveIngredients={firstFiveIngredients}
                  hasMoreIngredients={hasMoreIngredients}
                  onViewFull={handleViewFullClick}
                  onRemove={onRemoveFromDay ? handleRemove : undefined}
                  onClose={onClose}
                />
              </DialogPanel>
            </TransitionChild>
          </div>

          {/* Mobile bottom sheet positioning */}
          <div className="flex min-h-full items-end justify-center md:hidden">
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-full"
              enterTo="opacity-100 translate-y-0"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0"
              leaveTo="opacity-0 translate-y-full"
            >
              <DialogPanel className="relative z-50 max-h-[85vh] w-full transform overflow-hidden rounded-t-lg bg-white text-left align-middle shadow-xl transition-all">
                <RecipePreviewContent
                  recipe={recipe}
                  firstFiveIngredients={firstFiveIngredients}
                  hasMoreIngredients={hasMoreIngredients}
                  onViewFull={handleViewFullClick}
                  onRemove={onRemoveFromDay ? handleRemove : undefined}
                  onClose={onClose}
                  isMobile
                />
              </DialogPanel>
            </TransitionChild>
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
  onRemove?: () => void;
  onClose: () => void;
  isMobile?: boolean;
}

function RecipePreviewContent({
  recipe,
  firstFiveIngredients,
  hasMoreIngredients,
  onViewFull,
  onRemove,
  onClose,
  isMobile = false,
}: RecipePreviewContentProps) {
  return (
    <div className={clsx('p-6', isMobile && 'max-h-[85vh] overflow-y-auto')}>
      {/* Mobile handle bar */}
      {isMobile && (
        <div className="flex justify-center pb-4">
          <div className="h-1 w-10 rounded-full bg-gray-300" />
        </div>
      )}

      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <DialogTitle
          as="h3"
          className="pr-4 text-lg leading-6 font-semibold text-gray-900"
        >
          {recipe.title}
        </DialogTitle>
        {!isMobile && (
          <button
            onClick={onClose}
            className="flex-shrink-0 rounded-md text-gray-400 hover:text-gray-600 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            aria-label="Close preview"
          >
            <span className="sr-only">Close</span>
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Recipe description */}
      {recipe.description && (
        <p className="mb-4 text-sm leading-relaxed text-gray-600">
          {recipe.description}
        </p>
      )}



      {/* Key metadata */}
      <div className="mb-4 grid grid-cols-3 gap-4 text-sm">
        <div className="text-center">
          <div className="font-medium text-gray-900">
            {recipe.total_time_minutes}
          </div>
          <div className="text-gray-500">minutes</div>
        </div>
        <div className="text-center">
          <div className="font-medium text-gray-900 capitalize">
            {recipe.difficulty}
          </div>
          <div className="text-gray-500">difficulty</div>
        </div>
        <div className="text-center">
          <div className="font-medium text-gray-900">
            {recipe.serving_max
              ? `${recipe.serving_min}-${recipe.serving_max}`
              : recipe.serving_min}
          </div>
          <div className="text-gray-500">servings</div>
        </div>
      </div>

      {/* First 5 ingredients */}
      <div className="mb-6">
        <h4 className="mb-3 font-medium text-gray-900">Ingredients</h4>
        <ul className="space-y-2">
          {firstFiveIngredients.map((ingredient, index) => (
            <li
              key={ingredient.id || index}
              className="flex text-sm text-gray-700"
            >
              <span className="w-16 flex-shrink-0 font-medium">
                {ingredient.quantity_value || ''}{' '}
                {ingredient.quantity_unit || ''}
              </span>
              <span>{ingredient.name}</span>
            </li>
          ))}
        </ul>
        {hasMoreIngredients && (
          <p className="mt-2 text-sm text-gray-500">
            +{recipe.ingredients.length - 5} more ingredients
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 border-t pt-4">
        <Button variant="primary" className="flex-1" onClick={onViewFull}>
          View Full Recipe
        </Button>
        {onRemove && (
          <Button variant="danger" onClick={onRemove} className="flex-1">
            Remove from Day
          </Button>
        )}
      </div>
    </div>
  );
}
