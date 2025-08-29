import React, { useState } from 'react';
import { useLoaderData, useParams, useNavigate, Link } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Button } from '../components/ui/Button';
import { Dialog, DialogFooter } from '../components/ui/Dialog';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useRecipeStore } from '../stores/useRecipeStore';
import type { Recipe } from '../types/Recipe';

const RecipesDetail: React.FC = () => {
  // Get recipe data from loader
  const recipe = useLoaderData() as Recipe | null;
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
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
            <div className="text-center py-8">
              <h1 className="mb-4 text-2xl font-bold text-gray-900">Recipe Not Found</h1>
              <p className="text-gray-600 mb-6">
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
              <div className="flex justify-between items-start gap-4">
                <div className="flex-1 min-w-0">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">{recipe.title}</h1>
                  {recipe.description && (
                    <p className="text-lg text-gray-700 leading-relaxed">{recipe.description}</p>
                  )}
                </div>
                <div className="flex gap-2 flex-wrap">
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
            <Card variant="elevated" className="p-0 overflow-hidden">
              <div className="h-64 md:h-80 bg-gradient-to-br from-orange-100 to-orange-200 flex items-center justify-center">
                <div className="text-center text-orange-600">
                  <svg 
                    className="mx-auto h-16 w-16 mb-4" 
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
              <h2 id="recipe-details" className="sr-only">Recipe Details</h2>
              
              {/* Times and Servings */}
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4 mb-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-1">Prep Time</h3>
                  <p className="text-2xl font-bold text-orange-600">{recipe.prep_time_minutes}</p>
                  <p className="text-sm text-gray-600">minutes</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-1">Cook Time</h3>
                  <p className="text-2xl font-bold text-orange-600">{recipe.cook_time_minutes}</p>
                  <p className="text-sm text-gray-600">minutes</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-1">Total Time</h3>
                  <p className="text-2xl font-bold text-orange-600">{recipe.total_time_minutes}</p>
                  <p className="text-sm text-gray-600">minutes</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-1">Servings</h3>
                  <p className="text-2xl font-bold text-orange-600">
                    {recipe.serving_min}
                    {recipe.serving_max ? `-${recipe.serving_max}` : ''}
                  </p>
                  <p className="text-sm text-gray-600">people</p>
                </div>
              </div>

              {/* Tags */}
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-sm font-medium text-gray-700">Tags:</span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {recipe.category}
                </span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  {recipe.difficulty}
                </span>
                {recipe.ethnicity && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    {recipe.ethnicity}
                  </span>
                )}
                {recipe.oven_temperature_f && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    {recipe.oven_temperature_f}°F
                  </span>
                )}
              </div>
            </Card>
          </section>

          {/* Ingredients Section */}
          <section className="mb-6" aria-labelledby="ingredients-heading">
            <Card variant="elevated" className="p-6">
              <h2 id="ingredients-heading" className="text-2xl font-bold text-gray-900 mb-4">
                Ingredients
              </h2>
              <ul className="space-y-2" role="list">
                {recipe.ingredients.map((ingredient, index) => (
                  <li 
                    key={ingredient.id || index} 
                    className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-sm font-medium mt-0.5">
                      {index + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-gray-900">
                        {ingredient.quantity_value && ingredient.quantity_unit && (
                          <span className="font-semibold text-orange-600 mr-2">
                            {ingredient.quantity_value} {ingredient.quantity_unit}
                          </span>
                        )}
                        <span>{ingredient.name}</span>
                        {ingredient.prep?.method && (
                          <span className="text-gray-600 ml-1">
                            , {ingredient.prep.method}
                          </span>
                        )}
                        {ingredient.is_optional && (
                          <span className="text-gray-500 italic ml-1">(optional)</span>
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
              <h2 id="instructions-heading" className="text-2xl font-bold text-gray-900 mb-4">
                Instructions
              </h2>
              <ol className="space-y-4" role="list">
                {recipe.instructions.map((step, index) => (
                  <li 
                    key={index} 
                    className="flex gap-4 p-4 rounded-lg border border-gray-200 hover:border-orange-200 transition-colors"
                  >
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-orange-600 text-white flex items-center justify-center font-bold">
                      {index + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-gray-900 leading-relaxed">{step}</p>
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
                <h2 id="notes-heading" className="text-xl font-semibold text-gray-900 mb-3">
                  Notes
                </h2>
                <p className="text-gray-700 leading-relaxed">{recipe.user_notes}</p>
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
              This recipe will be removed from all meal plans and cannot be recovered.
            </p>
          </div>

          <DialogFooter
            cancelText="Cancel"
            confirmText={isDeleting ? "Deleting..." : "Delete Recipe"}
            onCancel={() => setIsDeleteModalOpen(false)}
            onConfirm={handleDelete}
            cancelProps={{ disabled: isDeleting }}
            confirmProps={{ 
              variant: 'danger', 
              disabled: isDeleting,
              loading: isDeleting
            }}
          />
        </Dialog>
      </div>
    </Container>
  );
};

export default RecipesDetail;
