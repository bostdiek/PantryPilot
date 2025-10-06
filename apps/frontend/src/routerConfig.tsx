import { lazy, Suspense } from 'react';
import { createBrowserRouter, redirect } from 'react-router-dom';
import HydrateFallback from './components/HydrateFallback';
import ProtectedRoute from './components/ProtectedRoute';
import Root from './components/Root';
import { LoadingSpinner } from './components/ui/LoadingSpinner';
import { useMealPlanStore } from './stores/useMealPlanStore';
import { useRecipeStore } from './stores/useRecipeStore';
import { useAuthStore } from './stores/useAuthStore';
import { getDraftById } from './api/endpoints/aiDrafts';
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
const UserProfilePage = lazy(() => import('./pages/UserProfilePage'));
const ComponentShowcase = lazy(() => import('./pages/dev/ComponentShowcase'));

// Loader functions for protected routes
const homeLoader = async () => {
  console.log('Home loader executing...');

  const { fetchRecipes } = useRecipeStore.getState();
  const { loadWeek } = useMealPlanStore.getState();

  try {
    // Start both fetches in parallel
    console.log('Starting parallel data fetching for home page');
    await Promise.all([fetchRecipes(), loadWeek()]);
    console.log('Home loader completed');
  } catch (error) {
    console.error('Home loader: failed to load data', error);
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
    console.error('Recipes loader: failed to load data', error);
    // Don't throw here - let the component handle the error state
  }

  return null;
};

const newRecipeLoader = async ({ request }: { request: Request }) => {
  const url = new URL(request.url);
  const ai = url.searchParams.get('ai');
  const draftId = url.searchParams.get('draftId');
  const token = url.searchParams.get('token');

  // Check if this is an AI draft deep link
  if (ai === '1' && draftId && token) {
    console.log('New recipe loader: AI draft deep link detected');

    // Check authentication - redirect to login if not authenticated
    const { token: authToken } = useAuthStore.getState();
    if (!authToken) {
      console.log('New recipe loader: User not authenticated, redirecting to login');
      // Preserve the full URL as the next parameter
      return redirect(`/login?next=${encodeURIComponent(url.pathname + url.search)}`);
    }

    try {
      // Fetch the draft
      const draftResponse = await getDraftById(draftId, token);
      console.log('New recipe loader: Draft fetched successfully', draftResponse);

      // Set the form from the suggestion
      const { setFormFromSuggestion } = useRecipeStore.getState();
      setFormFromSuggestion(draftResponse.payload);

      console.log('New recipe loader: Form prefilled from AI suggestion');
    } catch (error) {
      console.error('New recipe loader: Failed to load draft', error);
      // Don't throw - let the component handle the error state
      // The component can check for the error and show a friendly message
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
    console.error('Recipe detail loader: failed to load data', error);
    // Don't throw here - let the component handle the error state
  }

  return null;
};

const mealPlanLoader = async () => {
  // The ProtectedRoute component already handles authentication checks,
  // so we can safely assume the user is authenticated when this loader runs
  console.log('Meal plan loader: loading data for authenticated user');

  const { loadWeek } = useMealPlanStore.getState();
  const { recipes, fetchRecipes } = useRecipeStore.getState();

  try {
    await Promise.all([
      loadWeek(),
      recipes.length === 0 ? fetchRecipes() : Promise.resolve(),
    ]);
    console.log('Meal plan loader: data loaded successfully');
  } catch (error) {
    console.error('Meal plan loader: failed to load data', error);
    // Don't throw here - let the component handle the error state
  }

  return null;
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
