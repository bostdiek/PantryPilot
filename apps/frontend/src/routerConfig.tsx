import { createBrowserRouter } from 'react-router-dom';
import Root from './components/Root';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import MealPlanPage from './pages/MealPlanPage';
import RecipesDetail from './pages/RecipesDetail';
import NewRecipePage from './pages/RecipesNewPage';
import RecipesPage from './pages/RecipesPage';
import ComponentShowcase from './pages/dev/ComponentShowcase';
import { useMealPlanStore } from './stores/useMealPlanStore';
import { useRecipeStore } from './stores/useRecipeStore';

// Loader functions
const homeLoader = async () => {
  console.log('Home loader executing...');
  const { fetchRecipes } = useRecipeStore.getState();
  const { fetchCurrentWeek } = useMealPlanStore.getState();

  // Start both fetches in parallel
  console.log('Starting parallel data fetching for home page');
  await Promise.all([fetchRecipes(), fetchCurrentWeek()]);

  console.log('Home loader completed');
  // Data is already stored in our Zustand stores
  return null;
};

const recipesLoader = async () => {
  const { recipes, fetchRecipes } = useRecipeStore.getState();

  // Only fetch if we don't already have recipes
  if (recipes.length === 0) {
    await fetchRecipes();
  }

  return null;
};

const recipeDetailLoader = async ({ params }: { params: { id?: string } }) => {
  const { fetchRecipeById } = useRecipeStore.getState();
  if (params.id) {
    return fetchRecipeById(params.id);
  }
  return null;
};

const mealPlanLoader = async () => {
  const { fetchCurrentWeek } = useMealPlanStore.getState();
  await fetchCurrentWeek();
  return null;
};

// Create router with data loading
export const router = createBrowserRouter([
  {
    path: '/',
    element: <Root />,
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
        path: 'meal-plan',
        element: <MealPlanPage />,
        loader: mealPlanLoader,
      },
      {
        path: 'login',
        element: <LoginPage />,
      },
      {
        path: 'dev/components',
        element: <ComponentShowcase />,
      },
    ],
  },
]);
