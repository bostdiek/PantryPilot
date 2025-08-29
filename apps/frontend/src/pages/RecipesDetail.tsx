import React, { useState } from 'react';
import { Link, useLoaderData, useNavigate, useParams } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Dialog, DialogFooter } from '../components/ui/Dialog';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useRecipeStore } from '../stores/useRecipeStore';
import type { Recipe } from '../types/Recipe';

const RecipesDetail: React.FC = () => {
  // Get recipe data from loader as fallback
  const loaderRecipe = useLoaderData() as Recipe | null;
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Get recipe from store (primary source for latest data)
  const { recipes } = useRecipeStore();

  // Find the recipe in the store first, fallback to loader data
  const storeRecipe = id ? recipes.find((r) => r.id === id) : null;
  const recipe = storeRecipe || loaderRecipe;

  // State for delete confirmation modal
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // State for loading states
  const [isDuplicating, setIsDuplicating] = useState(false);

  // Store actions
  const { deleteRecipe, duplicateRecipe, isLoading } = useRecipeStore();

  // Handle delete action
  const handleDelete = async () => {
    if (!id) return;

    try {
      setIsDeleting(true);
      const success = await deleteRecipe(id);
      if (success) {
        navigate('/recipes', { replace: true });
      }
    } catch (error) {
      console.error('Failed to delete recipe:', error);
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  // Handle duplicate action
  const handleDuplicate = async () => {
    if (!id) return;

    try {
      setIsDuplicating(true);
      const duplicatedRecipe = await duplicateRecipe(id);
      if (duplicatedRecipe) {
        navigate(`/recipes/${duplicatedRecipe.id}`, { replace: true });
      }
    } catch (error) {
      console.error('Failed to duplicate recipe:', error);
    } finally {
      setIsDuplicating(false);
    }
  };

  // Handle edit action
  const handleEdit = () => {
    if (id) {
      navigate(`/recipes/${id}/edit`);
    }
  };

  // Show loading state if recipe is being fetched
  if (isLoading && !recipe) {
    return (
      <Container>
        <div className="py-8">
          <Card variant="elevated" className="p-6">
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
              <span className="ml-3 text-gray-600">Loading recipe...</span>
            </div>
          </Card>
        </div>
      </Container>
    );
  }

  // Show not found state
  if (!recipe) {
    return (
      <Container>
        <div className="py-8">
          <Card variant="elevated" className="p-6">
            <div className="py-8 text-center">
              <h1 className="mb-4 text-2xl font-bold text-gray-900">
                Recipe Not Found
              </h1>
              <p className="mb-6 text-gray-600">
                The recipe with ID "{id}" could not be found.
              </p>
              <Link to="/recipes">
                <Button variant="primary">Browse All Recipes</Button>
              </Link>
            </div>
          </Card>
        </div>
      </Container>
    );
  }

  return (
    <Container>
      <div className="py-8">
        <article>
          {/* Header with Actions */}
          <header className="mb-6">
            <Card variant="elevated" className="p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <h1 className="mb-2 text-3xl font-bold text-gray-900">
                    {recipe.title}
                  </h1>
                  {recipe.description && (
                    <p className="text-lg leading-relaxed text-gray-700">
                      {recipe.description}
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="md"
                    onClick={handleEdit}
                    aria-label={`Edit ${recipe.title}`}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="secondary"
                    size="md"
                    onClick={handleDuplicate}
                    disabled={isDuplicating}
                    loading={isDuplicating}
                    aria-label={`Duplicate ${recipe.title}`}
                  >
                    Duplicate
                  </Button>
                  <Button
                    variant="danger"
                    size="md"
                    onClick={() => setIsDeleteModalOpen(true)}
                    aria-label={`Delete ${recipe.title}`}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          </header>

          {/* Hero Image Placeholder */}
          <section className="mb-6" aria-labelledby="recipe-image">
            <Card variant="elevated" className="overflow-hidden p-0">
              <div className="flex h-64 items-center justify-center bg-gradient-to-br from-orange-100 to-orange-200 md:h-80">
                <div className="text-center text-orange-600">
                  <svg
                    className="mx-auto mb-4 h-16 w-16"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                  <p className="text-sm font-medium">Recipe Image</p>
                  <p className="text-xs opacity-75">Coming Soon</p>
                </div>
              </div>
            </Card>
          </section>

          {/* Recipe Metadata */}
          <section className="mb-6" aria-labelledby="recipe-details">
            <Card variant="elevated" className="p-6">
              <h2 id="recipe-details" className="sr-only">
                Recipe Details
              </h2>

              {/* Times and Servings */}
              <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="rounded-lg bg-gray-50 p-4 text-center">
                  <h3 className="mb-1 font-semibold text-gray-900">
                    Prep Time
                  </h3>
                  <p className="text-2xl font-bold text-orange-600">
                    {recipe.prep_time_minutes}
                  </p>
                  <p className="text-sm text-gray-600">minutes</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-4 text-center">
                  <h3 className="mb-1 font-semibold text-gray-900">
                    Cook Time
                  </h3>
                  <p className="text-2xl font-bold text-orange-600">
                    {recipe.cook_time_minutes}
                  </p>
                  <p className="text-sm text-gray-600">minutes</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-4 text-center">
                  <h3 className="mb-1 font-semibold text-gray-900">
                    Total Time
                  </h3>
                  <p className="text-2xl font-bold text-orange-600">
                    {recipe.total_time_minutes}
                  </p>
                  <p className="text-sm text-gray-600">minutes</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-4 text-center">
                  <h3 className="mb-1 font-semibold text-gray-900">Servings</h3>
                  <p className="text-2xl font-bold text-orange-600">
                    {recipe.serving_min}
                    {recipe.serving_max ? `-${recipe.serving_max}` : ''}
                  </p>
                  <p className="text-sm text-gray-600">people</p>
                </div>
              </div>

              {/* Tags */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-gray-700">Tags:</span>
                <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                  {recipe.category}
                </span>
                <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                  {recipe.difficulty}
                </span>
                {recipe.ethnicity && (
                  <span className="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800">
                    {recipe.ethnicity}
                  </span>
                )}
                {recipe.oven_temperature_f && (
                  <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                    {recipe.oven_temperature_f}°F
                  </span>
                )}
              </div>
            </Card>
          </section>

          {/* Ingredients Section */}
          <section className="mb-6" aria-labelledby="ingredients-heading">
            <Card variant="elevated" className="p-6">
              <h2
                id="ingredients-heading"
                className="mb-4 text-2xl font-bold text-gray-900"
              >
                Ingredients
              </h2>
              <ul className="space-y-2" role="list">
                {recipe.ingredients.map((ingredient, index) => (
                  <li
                    key={ingredient.id || index}
                    className="flex items-start gap-3 rounded-lg p-3 transition-colors hover:bg-gray-50"
                  >
                    <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-orange-100 text-sm font-medium text-orange-600">
                      {index + 1}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-gray-900">
                        {ingredient.quantity_value &&
                          ingredient.quantity_unit && (
                            <span className="mr-2 font-semibold text-orange-600">
                              {ingredient.quantity_value}{' '}
                              {ingredient.quantity_unit}
                            </span>
                          )}
                        <span>{ingredient.name}</span>
                        {ingredient.prep?.method && (
                          <span className="ml-1 text-gray-600">
                            , {ingredient.prep.method}
                          </span>
                        )}
                        {ingredient.is_optional && (
                          <span className="ml-1 text-gray-500 italic">
                            (optional)
                          </span>
                        )}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          </section>

          {/* Instructions Section */}
          <section aria-labelledby="instructions-heading">
            <Card variant="elevated" className="p-6">
              <h2
                id="instructions-heading"
                className="mb-4 text-2xl font-bold text-gray-900"
              >
                Instructions
              </h2>
              <ol className="space-y-4" role="list">
                {recipe.instructions.map((step, index) => (
                  <li
                    key={index}
                    className="flex gap-4 rounded-lg border border-gray-200 p-4 transition-colors hover:border-orange-200"
                  >
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-orange-600 font-bold text-white">
                      {index + 1}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="leading-relaxed text-gray-900">{step}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </Card>
          </section>

          {/* Additional Notes */}
          {recipe.user_notes && (
            <section className="mt-6" aria-labelledby="notes-heading">
              <Card variant="elevated" className="p-6">
                <h2
                  id="notes-heading"
                  className="mb-3 text-xl font-semibold text-gray-900"
                >
                  Notes
                </h2>
                <p className="leading-relaxed text-gray-700">
                  {recipe.user_notes}
                </p>
              </Card>
            </section>
          )}
        </article>

        {/* Delete Confirmation Modal */}
        <Dialog
          isOpen={isDeleteModalOpen}
          onClose={() => setIsDeleteModalOpen(false)}
          title="Delete Recipe"
          description="This action cannot be undone. This will permanently delete the recipe."
          size="md"
        >
          <div className="mt-4">
            <p className="text-gray-600">
              Are you sure you want to delete "<strong>{recipe.title}</strong>"?
              This recipe will be removed from all meal plans and cannot be
              recovered.
            </p>
          </div>

          <DialogFooter
            cancelText="Cancel"
            confirmText={isDeleting ? 'Deleting...' : 'Delete Recipe'}
            onCancel={() => setIsDeleteModalOpen(false)}
            onConfirm={handleDelete}
            cancelProps={{ disabled: isDeleting }}
            confirmProps={{
              variant: 'danger',
              disabled: isDeleting,
              loading: isDeleting,
            }}
          />
        </Dialog>
      </div>
    </Container>
  );
};

export default RecipesDetail;
