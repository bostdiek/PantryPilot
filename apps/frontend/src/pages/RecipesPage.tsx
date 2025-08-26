import React from 'react';
import { Link } from 'react-router-dom';
import { Grid } from '../components/layout/Grid';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Icon } from '../components/ui/Icon';
import ChefHatIcon from '../components/ui/icons/chef-hat.svg?react';
import { useRecipeStore } from '../stores/useRecipeStore';

const RecipesPage: React.FC = () => {
  const { recipes, isLoading } = useRecipeStore();

  return (
    <Container size="lg">
      <div className="flex items-center justify-between pt-6 pb-4">
        <h1 className="text-2xl font-bold">My Recipes</h1>
        <Link to="/recipes/new">
          <Button variant="primary">+ Add Recipe</Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="border-primary-500 h-8 w-8 animate-spin rounded-full border-4 border-t-transparent"></div>
        </div>
      ) : recipes.length > 0 ? (
        <Grid columns={3} gap={6}>
          {recipes.map((recipe) => (
            <Link key={recipe.id} to={`/recipes/${recipe.id}`}>
              <Card variant="elevated" className="p-4 hover:shadow-md">
                <h3 className="mb-2 text-lg font-medium">{recipe.title}</h3>
                {/* Additional recipe info can go here */}
              </Card>
            </Link>
          ))}
        </Grid>
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
    </Container>
  );
};

export default RecipesPage;
