import { redirect } from 'react-router-dom';
import { getDraftById, getDraftByIdOwner } from './api/endpoints/aiDrafts';
import { logger } from './lib/logger';
import { useAuthStore } from './stores/useAuthStore';
import { useMealPlanStore } from './stores/useMealPlanStore';
import { useRecipeStore } from './stores/useRecipeStore';
import { ApiErrorImpl } from './types/api';
import { getLocalStartOfSundayWeek, toLocalYyyyMmDd } from './utils/dateUtils';

/**
 * Removes AI draft query parameters from a URL and returns a redirect response.
 * Used to clean up the URL after processing AI draft deep links.
 */
const redirectToCleanUrl = (url: URL): Response => {
  const cleanUrl = new URL(url);
  cleanUrl.searchParams.delete('ai');
  cleanUrl.searchParams.delete('draftId');
  cleanUrl.searchParams.delete('token');
  return redirect(cleanUrl.pathname + cleanUrl.search);
};

export const homeLoader = async () => {
  logger.debug('Home loader executing...');

  const { fetchRecipes } = useRecipeStore.getState();
  const { loadWeek } = useMealPlanStore.getState();

  try {
    // Start both fetches in parallel
    logger.debug('Starting parallel data fetching for home page');
    // Use browser's local week start to ensure timezone consistency
    const localWeekStart = toLocalYyyyMmDd(
      getLocalStartOfSundayWeek(new Date())
    );
    await Promise.all([fetchRecipes(), loadWeek(localWeekStart)]);
    logger.debug('Home loader completed');
  } catch (error) {
    logger.error('Home loader: failed to load data', error);
    // Don't throw here - let the component handle the error state
  }

  // Data is already stored in our Zustand stores
  return null;
};

export const recipesLoader = async () => {
  const { recipes, fetchRecipes } = useRecipeStore.getState();

  try {
    // Only fetch if we don't already have recipes
    if (recipes.length === 0) {
      await fetchRecipes();
    }
  } catch (error) {
    logger.error('Recipes loader: failed to load data', error);
    // Don't throw here - let the component handle the error state
  }

  return null;
};

export const newRecipeLoader = async ({ request }: { request: Request }) => {
  const url = new URL(request.url);
  const ai = url.searchParams.get('ai');
  const draftId = url.searchParams.get('draftId');
  const token = url.searchParams.get('token');

  // Check if this is an AI draft deep link
  if (ai === '1' && draftId && token) {
    logger.debug('New recipe loader: AI draft deep link detected');

    // Check authentication - redirect to login if not authenticated
    const { token: authToken } = useAuthStore.getState();
    if (!authToken) {
      logger.debug(
        'New recipe loader: User not authenticated, redirecting to login'
      );
      // Preserve the full URL as the next parameter
      return redirect(
        `/login?next=${encodeURIComponent(url.pathname + url.search)}`
      );
    }

    try {
      // Fetch the draft
      const draftResponse = await getDraftById(draftId, token);
      logger.debug(
        'New recipe loader: Draft fetched successfully',
        draftResponse
      );

      // Set the form from the suggestion
      const { setFormFromSuggestion } = useRecipeStore.getState();
      setFormFromSuggestion(draftResponse.payload);

      logger.debug('New recipe loader: Form prefilled from AI suggestion');

      // Redirect to clean URL to remove token from address bar
      return redirectToCleanUrl(url);
    } catch (error) {
      logger.error('New recipe loader: Failed to load draft with token', error);

      // If the token is expired or invalid (401 status), try to fetch using owner auth as fallback
      // This allows users to still access their own drafts even if the token expired
      if (error instanceof ApiErrorImpl && error.status === 401) {
        logger.warn('Draft token expired, attempting to fetch as owner...');

        try {
          // Try to fetch using the owner-only endpoint (uses Bearer token)
          const draftResponse = await getDraftByIdOwner(draftId);
          logger.debug('Draft fetched successfully as owner');

          // Set the form from the suggestion
          const { setFormFromSuggestion } = useRecipeStore.getState();
          setFormFromSuggestion(draftResponse.payload);

          logger.debug(
            'New recipe loader: Form prefilled from AI suggestion (owner fallback)'
          );

          // Redirect to clean URL to remove token from address bar
          return redirectToCleanUrl(url);
        } catch (ownerError) {
          logger.error('Failed to fetch draft as owner', ownerError);
          // Redirect to clean new recipe page since we can't load the draft
          return redirectToCleanUrl(url);
        }
      }
    }
  }

  return null;
};

export const recipeDetailLoader = async ({
  params,
}: {
  params: { id?: string };
}) => {
  const { fetchRecipeById } = useRecipeStore.getState();

  try {
    if (params.id) {
      return await fetchRecipeById(params.id);
    }
  } catch (error) {
    logger.error('Recipe detail loader: failed to load data', error);
    // Don't throw here - let the component handle the error state
  }

  return null;
};

export const mealPlanLoader = async () => {
  // The ProtectedRoute component already handles authentication checks,
  // so we can safely assume the user is authenticated when this loader runs
  logger.debug('Meal plan loader: loading data for authenticated user');

  const { loadWeek } = useMealPlanStore.getState();
  const { recipes, fetchRecipes } = useRecipeStore.getState();

  try {
    // Use browser's local week start to ensure timezone consistency
    const localWeekStart = toLocalYyyyMmDd(
      getLocalStartOfSundayWeek(new Date())
    );
    await Promise.all([
      loadWeek(localWeekStart),
      recipes.length === 0 ? fetchRecipes() : Promise.resolve(),
    ]);
    logger.debug('Meal plan loader: data loaded successfully');
  } catch (error) {
    logger.error('Meal plan loader: failed to load data', error);
    // Don't throw here - let the component handle the error state
  }

  return null;
};
