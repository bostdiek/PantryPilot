import { createBrowserRouter } from 'react-router-dom';
import HydrateFallback from './components/HydrateFallback';
import ProtectedRoute from './components/ProtectedRoute';
import Root from './components/Root';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import MealPlanPage from './pages/MealPlanPage';
import RecipesDetail from './pages/RecipesDetail';
import RecipesEditPage from './pages/RecipesEditPage';
import NewRecipePage from './pages/RecipesNewPage';
import RecipesPage from './pages/RecipesPage';
import ComponentShowcase from './pages/dev/ComponentShowcase';
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
        element: <LoginPage />,
      },
      {
        path: 'dev/components',
        element: <ComponentShowcase />,
      },
      // Protected routes - require authentication
      {
        path: '/',
        element: <ProtectedRoute />,
        children: [
          {
            index: true,
            element: <HomePage />,
            loader: homeLoader,
          },
          {
            path: 'recipes',
            element: <RecipesPage />,
            loader: recipesLoader,
          },
          {
            path: 'recipes/new',
            element: <NewRecipePage />,
          },
          {
            path: 'recipes/:id',
            element: <RecipesDetail />,
            loader: recipeDetailLoader,
          },
          {
            path: 'recipes/:id/edit',
            element: <RecipesEditPage />,
            loader: recipeDetailLoader,
          },
          {
            path: 'meal-plan',
            element: <MealPlanPage />,
            loader: mealPlanLoader,
          },
        ],
      },
    ],
  },
]);
