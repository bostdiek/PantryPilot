import React from 'react';
import { useLoaderData, useParams } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import type { Recipe } from '../types/Recipe';

const RecipesDetail: React.FC = () => {
  // Get recipe data from loader
  const recipe = useLoaderData() as Recipe | null;
  const { id } = useParams<{ id: string }>();

  if (!recipe) {
    return (
      <Container>
        <div className="py-8">
          <Card variant="elevated" className="p-6">
            <h1 className="mb-4 text-2xl font-bold">Recipe Not Found</h1>
            <p>The recipe with ID {id} could not be found.</p>
          </Card>
        </div>
      </Container>
    );
  }

  return (
    <Container>
      <div className="py-8">
        <Card variant="elevated" className="p-6">
          <h1 className="mb-4 text-2xl font-bold">{recipe.title}</h1>

          {recipe.description && (
            <p className="mb-6 text-gray-700">{recipe.description}</p>
          )}

          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <h3 className="font-medium">Prep Time</h3>
              <p>{recipe.prep_time_minutes} mins</p>
            </div>
            <div>
              <h3 className="font-medium">Cook Time</h3>
              <p>{recipe.cook_time_minutes} mins</p>
            </div>
            <div>
              <h3 className="font-medium">Total Time</h3>
              <p>{recipe.total_time_minutes} mins</p>
            </div>
            <div>
              <h3 className="font-medium">Servings</h3>
              <p>
                {recipe.serving_min}
                {recipe.serving_max ? `-${recipe.serving_max}` : ''}
              </p>
            </div>
          </div>

          <div className="mb-6">
            <h2 className="mb-2 text-xl font-semibold">Ingredients</h2>
            <ul className="list-inside list-disc">
              {recipe.ingredients.map((ingredient, index) => (
                <li key={ingredient.id || index} className="mb-1">
                  {ingredient.quantity_value && ingredient.quantity_unit
                    ? `${ingredient.quantity_value} ${ingredient.quantity_unit} `
                    : ''}
                  {ingredient.name}
                  {ingredient.prep?.method && `, ${ingredient.prep.method}`}
                  {ingredient.is_optional && ' (optional)'}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="mb-2 text-xl font-semibold">Instructions</h2>
            <ol className="list-inside list-decimal">
              {recipe.instructions.map((step, index) => (
                <li key={index} className="mb-2">
                  {step}
                </li>
              ))}
            </ol>
          </div>
        </Card>
      </div>
    </Container>
  );
};

export default RecipesDetail;
