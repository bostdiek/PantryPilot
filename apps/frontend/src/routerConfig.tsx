import { lazy, Suspense } from 'react';
import { createBrowserRouter, redirect } from 'react-router-dom';
import { getDraftById, getDraftByIdOwner } from './api/endpoints/aiDrafts';
import HydrateFallback from './components/HydrateFallback';
import ProtectedRoute from './components/ProtectedRoute';
import Root from './components/Root';
import { LoadingSpinner } from './components/ui/LoadingSpinner';
import { logger } from './lib/logger';
import { useAuthStore } from './stores/useAuthStore';
import { useMealPlanStore } from './stores/useMealPlanStore';
import { useRecipeStore } from './stores/useRecipeStore';
import { ApiErrorImpl } from './types/api';
import {
  toLocalYyyyMmDd,
  getLocalStartOfSundayWeek,
} from './utils/dateUtils';
// Lazy loaded pages for code-splitting (use top-level `lazy` import)
const HomePage = lazy(() => import('./pages/HomePage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const MealPlanPage = lazy(() => import('./pages/MealPlanPage'));
const GroceryListPage = lazy(() => import('./pages/GroceryListPage'));
const RecipesDetail = lazy(() => import('./pages/RecipesDetail'));
const RecipesEditPage = lazy(() => import('./pages/RecipesEditPage'));
const NewRecipePage = lazy(() => import('./pages/RecipesNewPage'));
const RecipesPage = lazy(() => import('./pages/RecipesPage'));
const AssistantPage = lazy(() => import('./pages/AssistantPage'));
const UserProfilePage = lazy(() => import('./pages/UserProfilePage'));
const ComponentShowcase = lazy(() => import('./pages/dev/ComponentShowcase'));
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage'));
const ResendVerificationPage = lazy(
  () => import('./pages/ResendVerificationPage')
);
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'));

// Loader functions for protected routes
const homeLoader = async () => {
  logger.debug('Home loader executing...');

  const { fetchRecipes } = useRecipeStore.getState();
  const { loadWeek } = useMealPlanStore.getState();

  try {
    // Start both fetches in parallel
    logger.debug('Starting parallel data fetching for home page');
    // Use browser's local week start to ensure timezone consistency
    const localWeekStart = toLocalYyyyMmDd(getLocalStartOfSundayWeek(new Date()));
    await Promise.all([fetchRecipes(), loadWeek(localWeekStart)]);
    logger.debug('Home loader completed');
  } catch (error) {
    logger.error('Home loader: failed to load data', error);
    // Don't throw here - let the component handle the error state
  }

  // Data is already stored in our Zustand stores
  return null;
};

const recipesLoader = async () => {
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

const newRecipeLoader = async ({ request }: { request: Request }) => {
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

const recipeDetailLoader = async ({ params }: { params: { id?: string } }) => {
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

const mealPlanLoader = async () => {
  // The ProtectedRoute component already handles authentication checks,
  // so we can safely assume the user is authenticated when this loader runs
  logger.debug('Meal plan loader: loading data for authenticated user');

  const { loadWeek } = useMealPlanStore.getState();
  const { recipes, fetchRecipes } = useRecipeStore.getState();

  try {
    // Use browser's local week start to ensure timezone consistency
    const localWeekStart = toLocalYyyyMmDd(getLocalStartOfSundayWeek(new Date()));
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

// Export loaders for testing and reuse
export {
  homeLoader,
  mealPlanLoader,
  newRecipeLoader,
  recipeDetailLoader,
  recipesLoader,
};

// Create router with data loading
export const router = createBrowserRouter([
  {
    path: '/',
    element: <Root />,
    HydrateFallback,
    children: [
      {
        path: 'login',
        element: (
          <Suspense fallback={<LoadingSpinner />}>
            <LoginPage />
          </Suspense>
        ),
      },
      {
        path: 'register',
        element: (
          <Suspense fallback={<LoadingSpinner />}>
            <RegisterPage />
          </Suspense>
        ),
      },
      {
        path: 'verify-email',
        element: (
          <Suspense fallback={<LoadingSpinner />}>
            <VerifyEmailPage />
          </Suspense>
        ),
      },
      {
        path: 'resend-verification',
        element: (
          <Suspense fallback={<LoadingSpinner />}>
            <ResendVerificationPage />
          </Suspense>
        ),
      },
      {
        path: 'forgot-password',
        element: (
          <Suspense fallback={<LoadingSpinner />}>
            <ForgotPasswordPage />
          </Suspense>
        ),
      },
      {
        path: 'reset-password',
        element: (
          <Suspense fallback={<LoadingSpinner />}>
            <ResetPasswordPage />
          </Suspense>
        ),
      },
      // Development-only component showcase (excluded from production bundle)
      ...(import.meta.env.DEV
        ? [
            {
              path: 'dev/components',
              element: (
                <Suspense fallback={<LoadingSpinner />}>
                  <ComponentShowcase />
                </Suspense>
              ),
            },
          ]
        : []),
      // Protected routes - require authentication
      {
        path: '/',
        element: <ProtectedRoute />,
        children: [
          {
            index: true,
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <HomePage />
              </Suspense>
            ),
            loader: homeLoader,
          },
          {
            path: 'recipes',
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <RecipesPage />
              </Suspense>
            ),
            loader: recipesLoader,
          },
          {
            path: 'recipes/new',
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <NewRecipePage />
              </Suspense>
            ),
            loader: newRecipeLoader,
          },
          {
            path: 'recipes/:id',
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <RecipesDetail />
              </Suspense>
            ),
            loader: recipeDetailLoader,
          },
          {
            path: 'recipes/:id/edit',
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <RecipesEditPage />
              </Suspense>
            ),
            loader: recipeDetailLoader,
          },
          {
            path: 'meal-plan',
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <MealPlanPage />
              </Suspense>
            ),
            loader: mealPlanLoader,
          },
          {
            path: 'grocery-list',
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <GroceryListPage />
              </Suspense>
            ),
          },
          {
            path: 'assistant',
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <AssistantPage />
              </Suspense>
            ),
          },
          {
            path: 'user',
            element: (
              <Suspense fallback={<LoadingSpinner />}>
                <UserProfilePage />
              </Suspense>
            ),
          },
        ],
      },
    ],
  },
]);
