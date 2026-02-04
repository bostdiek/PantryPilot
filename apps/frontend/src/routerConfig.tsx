/* eslint-disable react-refresh/only-export-components */
import { lazy, Suspense } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import HydrateFallback from './components/HydrateFallback';
import ProtectedRoute from './components/ProtectedRoute';
import Root from './components/Root';
import { LoadingSpinner } from './components/ui/LoadingSpinner';
import {
  homeLoader,
  mealPlanLoader,
  newRecipeLoader,
  recipeDetailLoader,
  recipesLoader,
} from './loaders';
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
