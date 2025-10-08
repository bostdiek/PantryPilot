import { useEffect, useMemo, useState, type FC } from 'react';
import { Link } from 'react-router-dom';
import { Grid } from '../components/layout/Grid';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Icon } from '../components/ui/Icon';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import ChefHatIcon from '../components/ui/icons/chef-hat.svg?react';
import { useRecipeStore } from '../stores/useRecipeStore';
import { useRecipeFilters } from '../hooks/useRecipeFilters';
import { RecipeSearchFilters } from '../components/recipes/RecipeSearchFilters';
import { RecipePagination } from '../components/recipes/RecipePagination';
import { RecipeCard } from '../components/recipes/RecipeCard';
import { RecipeQuickPreview } from '../components/RecipeQuickPreview';
import { AddByUrlModal } from '../components/recipes/AddByUrlModal';
import type { Recipe } from '../types/Recipe';

const RecipesPage: FC = () => {
  const {
    recipes,
    filteredRecipes,
    isLoading,
    error,
    pagination,
    fetchRecipes,
    setPage,
  } = useRecipeStore();

  const { filters } = useRecipeFilters();

  // Recipe preview state
  const [previewRecipe, setPreviewRecipe] = useState<Recipe | null>(null);

  // Add by URL modal state
  const [isAddByUrlModalOpen, setIsAddByUrlModalOpen] = useState(false);

  // Fetch recipes on mount
  useEffect(() => {
    if (recipes.length === 0 && !isLoading && !error) {
      fetchRecipes();
    }
  }, [recipes.length, isLoading, error, fetchRecipes]);

  // Handle recipe preview
  const handleRecipePreview = (recipe: Recipe) => {
    setPreviewRecipe(recipe);
  };

  const handleClosePreview = () => {
    setPreviewRecipe(null);
  };

  // Calculate paginated recipes
  const paginatedRecipes = useMemo(() => {
    const startIndex = (pagination.page - 1) * pagination.pageSize;
    const endIndex = startIndex + pagination.pageSize;
    return filteredRecipes.slice(startIndex, endIndex);
  }, [filteredRecipes, pagination.page, pagination.pageSize]);

  // Calculate total pages
  const totalPages = Math.ceil(pagination.total / pagination.pageSize);

  // Check if any filters are active
  const hasActiveFilters =
    filters.query ||
    filters.categories.length > 0 ||
    filters.difficulties.length > 0 ||
    filters.cookTimeMin > 0 ||
    filters.cookTimeMax < 240 ||
    filters.includedIngredients.length > 0 ||
    filters.excludedIngredients.length > 0;

  return (
    <Container size="xl">
      {/* Header */}
      <div className="flex items-center justify-between pt-6 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Recipes</h1>
          {pagination.total > 0 && (
            <p className="mt-1 text-sm text-gray-500">
              {hasActiveFilters
                ? `${pagination.total} recipe${pagination.total !== 1 ? 's' : ''} found`
                : `${pagination.total} recipe${pagination.total !== 1 ? 's' : ''} total`}
            </p>
          )}
        </div>
        <div className="flex space-x-3">
          <Button
            variant="secondary"
            onClick={() => setIsAddByUrlModalOpen(true)}
          >
            Add by URL
          </Button>
          <Link to="/recipes/new">
            <Button variant="primary">+ Add Recipe</Button>
          </Link>
        </div>
      </div>

      {/* Search and Filters */}
      <RecipeSearchFilters className="mb-6" />

      {/* Content */}
      {isLoading ? (
        <Card variant="elevated" className="flex flex-col items-center py-16">
          <LoadingSpinner />
          <p className="mt-4 text-sm text-gray-600">Loading recipes...</p>
        </Card>
      ) : error ? (
        <Card variant="elevated" className="py-16">
          <ErrorMessage message={error} />
          <div className="mt-4 flex justify-center">
            <Button variant="outline" onClick={fetchRecipes}>
              Try Again
            </Button>
          </div>
        </Card>
      ) : paginatedRecipes.length > 0 ? (
        <div className="space-y-6">
          {/* Recipe Grid */}
          <Grid columns={3} gap={6} className="auto-rows-fr">
            {paginatedRecipes.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                enablePreview={true}
                onPreview={handleRecipePreview}
              />
            ))}
          </Grid>

          {/* Pagination */}
          <RecipePagination
            currentPage={pagination.page}
            totalPages={totalPages}
            pageSize={pagination.pageSize}
            totalItems={pagination.total}
            onPageChange={setPage}
            className="pt-6"
          />
        </div>
      ) : hasActiveFilters ? (
        <Card variant="elevated" className="flex flex-col items-center py-16">
          <Icon svg={ChefHatIcon} className="mb-4 h-12 w-12 text-gray-300" />
          <p className="mb-2 text-lg text-gray-700">
            No recipes match your filters
          </p>
          <p className="mb-4 text-center text-sm text-gray-600">
            Try adjusting your search criteria or clearing filters
          </p>
        </Card>
      ) : (
        <Card variant="elevated" className="flex flex-col items-center py-16">
          <Icon svg={ChefHatIcon} className="mb-4 h-12 w-12 text-gray-300" />
          <p className="mb-2 text-lg text-gray-700">No recipes yet</p>
          <p className="mb-4 text-center text-sm text-gray-600">
            Start by adding your first recipe
          </p>
          <Link to="/recipes/new">
            <Button variant="primary">Add Your First Recipe</Button>
          </Link>
        </Card>
      )}

      {/* Recipe Quick Preview Modal */}
      <RecipeQuickPreview
        isOpen={!!previewRecipe}
        onClose={handleClosePreview}
        recipe={previewRecipe}
        // No dateContext for search page - no "Remove from Day" functionality
      />

      {/* Add by URL Modal */}
      <AddByUrlModal
        isOpen={isAddByUrlModalOpen}
        onClose={() => setIsAddByUrlModalOpen(false)}
      />
    </Container>
  );
};

export default RecipesPage;
