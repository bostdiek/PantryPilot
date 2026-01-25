/**
 * MealProposalBlock component for rendering interactive meal plan proposals.
 *
 * Displays a day-specific meal proposal with recipe details and
 * Accept/Reject buttons. Used during conversational meal planning
 * workflow with Nibble.
 *
 * Behavior:
 * - Existing recipes: Accept button adds directly to meal plan
 * - New recipes: Two buttons - "Save to Recipe Book" and "Add to Meal Plan"
 *   - Save to Recipe Book: Navigates to recipe creation with prefilled data
 *   - Add to Meal Plan: Shows warning that recipe must be saved first
 * - Leftover/Eating out: Accept adds special entry to meal plan
 * - Reject: Marks proposal as rejected, prompts agent for alternatives
 */

import {
  BookOpen,
  Calendar,
  Check,
  ChefHat,
  ExternalLink,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { createMealEntry } from '../../../api/endpoints/mealPlans';
import { useChatStore } from '../../../stores/useChatStore';
import type { MealProposalBlock as MealProposalBlockType } from '../../../types/Chat';
import {
  getMealProposalStatus,
  markMealProposalAddedToPlan,
  markMealProposalRejected,
} from '../../../utils/mealProposalStatus';

interface MealProposalBlockProps {
  block: MealProposalBlockType;
}

type ProposalState =
  | 'pending'
  | 'accepted'
  | 'rejected'
  | 'saving_to_book'
  | 'saved_to_book'
  | 'needs_save_warning';

function parseIsoDateAsLocal(isoDate: string): Date | null {
  // Avoid JS Date parsing quirks where "YYYY-MM-DD" is treated as UTC,
  // which can render as the prior day in negative timezones.
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (!match) return null;
  const year = Number(match[1]);
  const monthIndex = Number(match[2]) - 1;
  const day = Number(match[3]);
  if (Number.isNaN(year) || Number.isNaN(monthIndex) || Number.isNaN(day))
    return null;
  return new Date(year, monthIndex, day);
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
  const [state, setState] = useState<ProposalState>('pending');
  const [isLoading, setIsLoading] = useState(false);

  const proposalKey = useMemo(() => {
    const parts: Array<string> = [block.proposal_id];
    if (block.existing_recipe?.id)
      parts.push(`existing:${block.existing_recipe.id}`);
    if (block.new_recipe?.source_url)
      parts.push(`url:${block.new_recipe.source_url}`);
    if (block.new_recipe?.title) parts.push(`title:${block.new_recipe.title}`);
    if (block.is_leftover) parts.push('leftover');
    if (block.is_eating_out) parts.push('eating_out');
    return parts.join('|');
  }, [
    block.proposal_id,
    block.existing_recipe?.id,
    block.new_recipe?.source_url,
    block.new_recipe?.title,
    block.is_leftover,
    block.is_eating_out,
  ]);

  const [persistedStatus, setPersistedStatus] = useState(() =>
    getMealProposalStatus(proposalKey)
  );

  useEffect(() => {
    const status = getMealProposalStatus(proposalKey);
    setPersistedStatus(status);
    if (status.addedToPlan) {
      setState('accepted');
    } else if (status.rejected) {
      setState('rejected');
    } else if (status.savedToBook) {
      setState('saved_to_book');
    }
  }, [proposalKey]);

  const newRecipeSourceUrl = block.new_recipe?.source_url ?? undefined;

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
        notes: block.notes ?? undefined,
      });
      markMealProposalAddedToPlan(proposalKey);
      setPersistedStatus((prev) => ({ ...prev, addedToPlan: true }));
      setState('accepted');

      useChatStore
        .getState()
        .appendLocalAssistantMessage(
          `Added to your meal plan for ${block.day_label} (${block.date}). What day should we plan next?`
        );
    } catch (error) {
      console.error('Failed to add meal entry:', error);
      alert('Failed to add meal to plan. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle saving new recipe to recipe book.
   * Navigates to recipe creation page with prefilled data from the AI suggestion.
   * Also passes the meal plan date so the recipe can be added after saving.
   */
  const handleSaveToRecipeBook = () => {
    if (!block.new_recipe) return;

    // Build URL params for prefilling the recipe form
    const params = new URLSearchParams();
    if (newRecipeSourceUrl) {
      params.set('url', newRecipeSourceUrl);
    }
    if (block.new_recipe.title) {
      params.set('title', block.new_recipe.title);
    }
    // Pass the meal plan date so we can add it after saving
    params.set('mealPlanDate', block.date);
    params.set('mealPlanDayLabel', block.day_label);
    params.set('proposalKey', proposalKey);
    // Opt-in redirect back to chat after successfully adding to the meal plan.
    // Keeps normal /recipes/new usage unchanged.
    params.set('returnToAssistant', '1');

    const conversationId = useChatStore.getState().activeConversationId;
    if (conversationId) {
      params.set('chatConversationId', conversationId);
    }

    setState('saving_to_book');

    // Navigate to recipe creation; returnToAssistant flag will bring the user
    // back to chat after the recipe is saved and added to the meal plan.
    navigate(`/recipes/new?${params.toString()}`);
  };

  /**
   * Handle attempt to add new recipe to meal plan.
   * Shows a warning that the recipe must be saved first.
   */
  const handleAddNewToMealPlan = () => {
    if (persistedStatus.addedToPlan) {
      setState('accepted');
      return;
    }

    if (persistedStatus.savedToBook) {
      setState('saved_to_book');
      return;
    }

    setState('needs_save_warning');
  };

  /**
   * Dismiss the warning and return to pending state.
   */
  const handleDismissWarning = () => {
    setState('pending');
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
        notes: block.notes ?? undefined,
      });
      markMealProposalAddedToPlan(proposalKey);
      setPersistedStatus((prev) => ({ ...prev, addedToPlan: true }));
      setState('accepted');

      useChatStore
        .getState()
        .appendLocalAssistantMessage(
          `Added to your meal plan for ${block.day_label} (${block.date}). Want me to suggest another day?`
        );
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
    } else if (block.is_leftover || block.is_eating_out) {
      await handleAcceptSpecial();
    }
    // Note: new_recipe has its own buttons, not handled here
  };

  const handleReject = () => {
    markMealProposalRejected(proposalKey);
    setPersistedStatus((prev) => ({ ...prev, rejected: true }));
    setState('rejected');
  };

  // Format date for display
  const formatDate = (isoDate: string) => {
    const date = parseIsoDateAsLocal(isoDate) ?? new Date(isoDate);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDomain = (urlString: string) => {
    try {
      return new URL(urlString).hostname;
    } catch {
      return urlString;
    }
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

  if (state === 'saving_to_book') {
    return (
      <div className="my-2 rounded-lg border border-blue-200 bg-blue-50 p-4">
        <div className="flex items-center gap-2 text-blue-700">
          <BookOpen className="h-5 w-5" />
          <span className="font-medium">Recipe creation opened</span>
        </div>
        <p className="mt-2 text-sm text-blue-600">
          Finish saving the recipe, and it will be added to {block.day_label}.
          You can keep the chat open while you do this.
        </p>
      </div>
    );
  }

  if (state === 'saved_to_book') {
    return (
      <div className="my-2 rounded-lg border border-blue-200 bg-blue-50 p-4">
        <div className="flex items-center gap-2 text-blue-700">
          <BookOpen className="h-5 w-5" />
          <span className="font-medium">Saved to your recipe book</span>
        </div>
        <p className="mt-2 text-sm text-blue-600">
          If you chose “Add to Meal Plan”, it should now appear on{' '}
          {block.day_label}.
        </p>
      </div>
    );
  }

  if (state === 'needs_save_warning') {
    return (
      <div className="my-2 rounded-lg border-2 border-amber-300 bg-amber-50 p-4 shadow-sm">
        <div className="mb-3 flex items-center gap-2 text-amber-800">
          <BookOpen className="h-5 w-5" />
          <span className="font-semibold">Recipe Not Saved Yet</span>
        </div>
        <p className="mb-4 text-sm text-amber-700">
          This recipe needs to be saved to your recipe book before it can be
          added to your meal plan. Would you like to save it first?
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            onClick={handleSaveToRecipeBook}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700"
          >
            <BookOpen className="h-4 w-4" />
            Save to Recipe Book
          </button>
          <button
            onClick={handleDismissWarning}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-gray-200 px-4 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-300"
          >
            Back
          </button>
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
            <div className="h-16 w-16 shrink-0 overflow-hidden rounded-md bg-gray-100">
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
            <div className="h-16 w-16 shrink-0 overflow-hidden rounded-md bg-gray-100">
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
              {newRecipeSourceUrl && (
                <a
                  href={newRecipeSourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex w-full items-center justify-between gap-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-blue-700 transition-colors hover:border-blue-300 hover:bg-blue-50"
                >
                  <span className="min-w-0 truncate">
                    View source ({formatDomain(newRecipeSourceUrl)})
                  </span>
                  <ExternalLink className="h-4 w-4 shrink-0" />
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
      <div className="flex flex-col gap-2">
        {/* For new recipes, show two accept buttons */}
        {block.new_recipe && (
          <>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <button
                onClick={handleSaveToRecipeBook}
                disabled={
                  isLoading ||
                  persistedStatus.savedToBook ||
                  persistedStatus.addedToPlan
                }
                className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
              >
                <BookOpen className="h-4 w-4" />
                {persistedStatus.savedToBook ? 'Saved' : 'Save to Recipe Book'}
              </button>
              <button
                onClick={handleAddNewToMealPlan}
                disabled={
                  isLoading ||
                  persistedStatus.savedToBook ||
                  persistedStatus.addedToPlan
                }
                className="inline-flex items-center justify-center gap-2 rounded-md bg-green-600 px-4 py-2 font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400"
              >
                <Calendar className="h-4 w-4" />
                {persistedStatus.addedToPlan ? 'Added' : 'Add to Meal Plan'}
              </button>
            </div>
            <button
              onClick={handleReject}
              disabled={
                isLoading ||
                persistedStatus.rejected ||
                persistedStatus.addedToPlan
              }
              className="inline-flex items-center justify-center gap-2 rounded-md bg-gray-200 px-4 py-2 font-medium text-gray-800 transition-colors hover:bg-gray-300 disabled:cursor-not-allowed"
            >
              <X className="h-4 w-4" />
              Reject
            </button>
          </>
        )}

        {/* For existing recipes and special entries, show single accept/reject */}
        {!block.new_recipe && (
          <div className="flex gap-2">
            <button
              onClick={handleAccept}
              disabled={isLoading || persistedStatus.addedToPlan}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-green-600 px-4 py-2 font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              <Check className="h-4 w-4" />
              {isLoading ? 'Adding...' : 'Accept'}
            </button>
            <button
              onClick={handleReject}
              disabled={
                isLoading ||
                persistedStatus.rejected ||
                persistedStatus.addedToPlan
              }
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-gray-200 px-4 py-2 font-medium text-gray-800 transition-colors hover:bg-gray-300 disabled:cursor-not-allowed"
            >
              <X className="h-4 w-4" />
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
