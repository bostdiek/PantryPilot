import { lazy, Suspense } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import HydrateFallback from './components/HydrateFallback';
import ProtectedRoute from './components/ProtectedRoute';
import Root from './components/Root';
import { LoadingSpinner } from './components/ui/LoadingSpinner';
// Lazy loaded pages for code-splitting
const HomePage = lazy(() => import('./pages/HomePage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const MealPlanPage = lazy(() => import('./pages/MealPlanPage'));
const RecipesDetail = lazy(() => import('./pages/RecipesDetail'));
const RecipesEditPage = lazy(() => import('./pages/RecipesEditPage'));
const NewRecipePage = lazy(() => import('./pages/RecipesNewPage'));
const RecipesPage = lazy(() => import('./pages/RecipesPage'));
const ComponentShowcase = lazy(() => import('./pages/dev/ComponentShowcase'));
import { useAuthStore } from './stores/useAuthStore';
import { useMealPlanStore } from './stores/useMealPlanStore';
import { useRecipeStore } from './stores/useRecipeStore';

// Loader functions with auth checks
const homeLoader = async () => {
  console.log('Home loader executing...');
  const { hasHydrated, token } = useAuthStore.getState();
  const isAuthenticated = token !== null;

  // Wait for hydration and check authentication
  if (!hasHydrated || !isAuthenticated) {
    console.log('Home loader: not authenticated, skipping data fetch');
    return null;
  }

  const { fetchRecipes } = useRecipeStore.getState();
  const { loadWeek } = useMealPlanStore.getState();

  // Start both fetches in parallel
  console.log('Starting parallel data fetching for home page');
  await Promise.all([fetchRecipes(), loadWeek()]);

  console.log('Home loader completed');
  // Data is already stored in our Zustand stores
  return null;
};

const recipesLoader = async () => {
  const { hasHydrated, token } = useAuthStore.getState();
  const isAuthenticated = token !== null;

  // Wait for hydration and check authentication
  if (!hasHydrated || !isAuthenticated) {
    console.log('Recipes loader: not authenticated, skipping data fetch');
    return null;
  }

  const { recipes, fetchRecipes } = useRecipeStore.getState();

  // Only fetch if we don't already have recipes
  if (recipes.length === 0) {
    await fetchRecipes();
  }

  return null;
};

const recipeDetailLoader = async ({ params }: { params: { id?: string } }) => {
  const { hasHydrated, token } = useAuthStore.getState();
  const isAuthenticated = token !== null;

  // Wait for hydration and check authentication
  if (!hasHydrated || !isAuthenticated) {
    console.log('Recipe detail loader: not authenticated, skipping data fetch');
    return null;
  }

  const { fetchRecipeById } = useRecipeStore.getState();
  if (params.id) {
    return fetchRecipeById(params.id);
  }
  return null;
};

const mealPlanLoader = async () => {
  const { hasHydrated, token } = useAuthStore.getState();
  const isAuthenticated = token !== null;

  // Wait for hydration and check authentication
  if (!hasHydrated || !isAuthenticated) {
    console.log('Meal plan loader: not authenticated, skipping data fetch');
    return null;
  }

  const { loadWeek } = useMealPlanStore.getState();
  const { recipes, fetchRecipes } = useRecipeStore.getState();
  await Promise.all([
    loadWeek(),
    recipes.length === 0 ? fetchRecipes() : Promise.resolve(),
  ]);
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
        ],
      },
    ],
  },
]);
