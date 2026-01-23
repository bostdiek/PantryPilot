/**
 * MealProposalBlock component for rendering interactive meal plan proposals.
 *
 * Displays a day-specific meal proposal with recipe details and
 * Accept/Reject buttons. Used during conversational meal planning
 * workflow with Nibble.
 *
 * Behavior:
 * - Existing recipes: Accept button adds directly to meal plan
 * - New recipes: Accept button prompts to save recipe first
 * - Leftover/Eating out: Accept adds special entry to meal plan
 * - Reject: Marks proposal as rejected, prompts agent for alternatives
 */

import { Calendar, Check, ChefHat, ExternalLink, X } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { createMealEntry } from '../../../api/endpoints/mealPlans';
import type { MealProposalBlock as MealProposalBlockType } from '../../../types/Chat';

interface MealProposalBlockProps {
  block: MealProposalBlockType;
}

/**
 * Renders an interactive meal proposal card for a specific day.
 *
 * Supports:
 * - Existing recipes from user's collection
 * - New recipes from web search
 * - Leftover days
 * - Eating out days
 */
export function MealProposalBlock({ block }: MealProposalBlockProps) {
  const navigate = useNavigate();
  const [state, setState] = useState<'pending' | 'accepted' | 'rejected'>(
    'pending'
  );
  const [isLoading, setIsLoading] = useState(false);

  const handleAcceptExisting = async () => {
    if (!block.existing_recipe?.id) return;

    setIsLoading(true);
    try {
      await createMealEntry({
        plannedForDate: block.date,
        mealType: 'dinner',
        recipeId: block.existing_recipe.id,
        isLeftover: block.is_leftover || false,
        isEatingOut: block.is_eating_out || false,
        notes: block.notes,
      });
      setState('accepted');
    } catch (error) {
      console.error('Failed to add meal entry:', error);
      alert('Failed to add meal to plan. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAcceptNew = () => {
    // For new recipes, prompt user to save first
    // In the future, this could trigger suggest_recipe automatically
    setState('accepted');
    alert(
      'Please ask Nibble to save this recipe first, then we can add it to your plan!'
    );
  };

  const handleAcceptSpecial = async () => {
    // Handle leftover or eating out entries
    setIsLoading(true);
    try {
      await createMealEntry({
        plannedForDate: block.date,
        mealType: 'dinner',
        isLeftover: block.is_leftover || false,
        isEatingOut: block.is_eating_out || false,
        notes: block.notes,
      });
      setState('accepted');
    } catch (error) {
      console.error('Failed to add meal entry:', error);
      alert('Failed to add meal to plan. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAccept = async () => {
    if (block.existing_recipe) {
      await handleAcceptExisting();
    } else if (block.new_recipe) {
      handleAcceptNew();
    } else {
      await handleAcceptSpecial();
    }
  };

  const handleReject = () => {
    setState('rejected');
  };

  // Format date for display
  const formatDate = (isoDate: string) => {
    const date = new Date(isoDate);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  };

  // Render based on state
  if (state === 'accepted') {
    return (
      <div className="my-2 rounded-lg border border-green-200 bg-green-50 p-4">
        <div className="flex items-center gap-2 text-green-700">
          <Check className="h-5 w-5" />
          <span className="font-medium">Added to {block.day_label}! 🎉</span>
        </div>
      </div>
    );
  }

  if (state === 'rejected') {
    return (
      <div className="my-2 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="flex items-center gap-2 text-gray-600">
          <X className="h-5 w-5" />
          <span className="font-medium">
            Rejected - Nibble will suggest alternatives
          </span>
        </div>
      </div>
    );
  }

  // Pending state - show interactive proposal
  return (
    <div className="my-2 rounded-lg border-2 border-blue-200 bg-white p-4 shadow-sm">
      {/* Day header with badge */}
      <div className="mb-3 flex items-center gap-2">
        <Calendar className="h-4 w-4 text-blue-600" />
        <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-sm font-semibold text-blue-800">
          {block.day_label}
        </span>
        <span className="text-sm text-gray-500">{formatDate(block.date)}</span>
      </div>

      {/* Recipe option - Existing Recipe */}
      {block.existing_recipe && (
        <div className="mb-4">
          <div className="flex items-start gap-3">
            {/* Recipe image or placeholder */}
            <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-md bg-gray-100">
              {block.existing_recipe.image_url ? (
                <img
                  src={block.existing_recipe.image_url}
                  alt={block.existing_recipe.title}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center">
                  <ChefHat className="h-8 w-8 text-gray-400" />
                </div>
              )}
            </div>

            {/* Recipe info */}
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center gap-2">
                <span className="inline-flex items-center rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                  From Your Recipes
                </span>
              </div>
              <h4 className="font-semibold text-gray-900">
                {block.existing_recipe.title}
              </h4>
              {block.existing_recipe.detail_path && (
                <button
                  onClick={() => navigate(block.existing_recipe!.detail_path!)}
                  className="mt-1 text-sm text-blue-600 hover:underline"
                >
                  View recipe →
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Recipe option - New Recipe */}
      {block.new_recipe && (
        <div className="mb-4">
          <div className="flex items-start gap-3">
            <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-md bg-gray-100">
              <div className="flex h-full w-full items-center justify-center">
                <ChefHat className="h-8 w-8 text-gray-400" />
              </div>
            </div>

            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center gap-2">
                <span className="inline-flex items-center rounded-md bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
                  New Recipe
                </span>
              </div>
              <h4 className="font-semibold text-gray-900">
                {block.new_recipe.title}
              </h4>
              {block.new_recipe.description && (
                <p className="mt-1 text-sm text-gray-600">
                  {block.new_recipe.description}
                </p>
              )}
              {block.new_recipe.source_url && (
                <a
                  href={block.new_recipe.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                >
                  View source
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Special entries - Leftover or Eating Out */}
      {!block.existing_recipe && !block.new_recipe && (
        <div className="mb-4">
          {block.is_leftover && (
            <div className="rounded-md bg-blue-50 p-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🍲</span>
                <div>
                  <p className="font-medium text-gray-900">Leftover Day</p>
                  {block.notes && (
                    <p className="text-sm text-gray-600">{block.notes}</p>
                  )}
                </div>
              </div>
            </div>
          )}
          {block.is_eating_out && (
            <div className="rounded-md bg-purple-50 p-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🍽️</span>
                <div>
                  <p className="font-medium text-gray-900">Eating Out</p>
                  {block.notes && (
                    <p className="text-sm text-gray-600">{block.notes}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Optional notes */}
      {block.notes && (block.existing_recipe || block.new_recipe) && (
        <div className="mb-4 rounded-md bg-gray-50 p-3">
          <p className="text-sm text-gray-700">{block.notes}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleAccept}
          disabled={isLoading}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-green-600 px-4 py-2 font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          <Check className="h-4 w-4" />
          {isLoading ? 'Adding...' : 'Accept'}
        </button>
        <button
          onClick={handleReject}
          disabled={isLoading}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-gray-200 px-4 py-2 font-medium text-gray-800 transition-colors hover:bg-gray-300 disabled:cursor-not-allowed"
        >
          <X className="h-4 w-4" />
          Reject
        </button>
      </div>
    </div>
  );
}
