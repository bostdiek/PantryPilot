import React, { useState, useEffect } from 'react';
import { useNavigate, useLoaderData, useParams } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select, type SelectOption } from '../components/ui/Select';
import { useRecipeStore } from '../stores/useRecipeStore';
import type { Ingredient } from '../types/Ingredients';
import type { Recipe } from '../types/Recipe';
import {
  RECIPE_CATEGORIES,
  RECIPE_DIFFICULTIES,
  type RecipeCategory,
  type RecipeDifficulty,
} from '../types/Recipe';

// Create options for the Select component
const categoryOptions: SelectOption[] = RECIPE_CATEGORIES.map((cat) => ({
  id: cat,
  name: cat.charAt(0).toUpperCase() + cat.slice(1), // Capitalize first letter
}));

const difficultyOptions: SelectOption[] = RECIPE_DIFFICULTIES.map((diff) => ({
  id: diff,
  name: diff.charAt(0).toUpperCase() + diff.slice(1), // Capitalize first letter
}));

const RecipesEditPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const recipe = useLoaderData() as Recipe | null;
  
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<SelectOption>(
    categoryOptions.find((c) => c.id === 'dinner') || categoryOptions[0]
  );
  const [difficulty, setDifficulty] = useState<SelectOption>(
    difficultyOptions.find((d) => d.id === 'medium') || difficultyOptions[0]
  );
  const [prepTime, setPrepTime] = useState(0);
  const [cookTime, setCookTime] = useState(0);
  const [servingMin, setServingMin] = useState(1);
  const [servingMax, setServingMax] = useState<number | undefined>(undefined);
  const [ethnicity, setEthnicity] = useState('');
  const [ovenTemperatureF, setOvenTemperatureF] = useState<number | undefined>(
    undefined
  );
  const [userNotes, setUserNotes] = useState('');
  const [ingredients, setIngredients] = useState<Ingredient[]>([
    {
      name: '',
      quantity_value: undefined,
      quantity_unit: '',
      prep: {},
      is_optional: false,
    },
  ]);
  const [instructions, setInstructions] = useState(['']);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { updateRecipe } = useRecipeStore();

  // Populate form fields when recipe data is available
  useEffect(() => {
    if (recipe) {
      setTitle(recipe.title);
      setDescription(recipe.description || '');
      setCategory(
        categoryOptions.find((c) => c.id === recipe.category) ||
          categoryOptions[0]
      );
      setDifficulty(
        difficultyOptions.find((d) => d.id === recipe.difficulty) ||
          difficultyOptions[0]
      );
      setPrepTime(recipe.prep_time_minutes || 0);
      setCookTime(recipe.cook_time_minutes || 0);
      setServingMin(recipe.serving_min || 1);
      setServingMax(recipe.serving_max || undefined);
      setEthnicity(recipe.ethnicity || '');
      setOvenTemperatureF(recipe.oven_temperature_f || undefined);
      setUserNotes(recipe.user_notes || '');
      
      // Set ingredients, ensuring we have at least one empty ingredient
      if (recipe.ingredients && recipe.ingredients.length > 0) {
        setIngredients(recipe.ingredients.map(ing => ({
          name: ing.name || '',
          quantity_value: ing.quantity_value || undefined,
          quantity_unit: ing.quantity_unit || '',
          prep: ing.prep || {},
          is_optional: ing.is_optional || false,
        })));
      }
      
      // Set instructions, ensuring we have at least one empty instruction
      if (recipe.instructions && recipe.instructions.length > 0) {
        setInstructions(recipe.instructions);
      }
    }
  }, [recipe]);

  // Show loading state if recipe is not loaded
  if (!recipe) {
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!id) {
      setError('Recipe ID is missing');
      return;
    }

    // Clear previous errors
    setError(null);
    setIsSubmitting(true);

    // Filter out empty instructions and ingredients
    const filteredInstructions = instructions.filter(
      (step) => step.trim() !== ''
    );
    const filteredIngredients = ingredients.filter(
      (ing) => ing.name.trim() !== ''
    );

    // Client-side validation: require at least one ingredient and one instruction
    if (filteredIngredients.length === 0) {
      setError('Please add at least one ingredient.');
      setIsSubmitting(false);
      return;
    }

    if (filteredInstructions.length === 0) {
      setError('Please add at least one instruction.');
      setIsSubmitting(false);
      return;
    }

    try {
      // Create the recipe update data object
      const recipeUpdateData = {
        title,
        description,
        category: category.id as RecipeCategory,
        difficulty: difficulty.id as RecipeDifficulty,
        prep_time_minutes: prepTime,
        cook_time_minutes: cookTime,
        serving_min: servingMin,
        serving_max: servingMax,
        ethnicity: ethnicity || undefined,
        oven_temperature_f: ovenTemperatureF,
        user_notes: userNotes || undefined,
        instructions: filteredInstructions,
        ingredients: filteredIngredients.map((ing) => ({
          name: ing.name,
          quantity_value: ing.quantity_value,
          quantity_unit: ing.quantity_unit || undefined,
          prep:
            ing.prep && (ing.prep.method || ing.prep.size_descriptor)
              ? {
                  method: ing.prep.method,
                  size_descriptor: ing.prep.size_descriptor,
                }
              : undefined,
          is_optional: ing.is_optional || false,
        })),
      };

      // Use the store to update the recipe
      const result = await updateRecipe(id, recipeUpdateData);

      if (result) {
        // Navigate back to the recipe detail page on success
        navigate(`/recipes/${id}`);
      } else {
        setError('Failed to update recipe. Please try again.');
      }
    } catch (err) {
      console.error('Failed to update recipe:', err);
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to update recipe. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Container size="md">
      <Card variant="default" className="mt-6 p-6">
        <h1 className="mb-4 text-2xl font-bold">Edit Recipe</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name & Description */}
          <Input
            label="Recipe Name"
            value={title}
            onChange={setTitle}
            placeholder="Enter recipe name"
            required
          />
          <Input
            label="Description"
            value={description}
            onChange={setDescription}
            placeholder="Brief description of the recipe"
          />

          {/* Category and Difficulty */}
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Category"
              options={categoryOptions}
              value={category}
              onChange={setCategory}
            />

            <Select
              label="Difficulty"
              options={difficultyOptions}
              value={difficulty}
              onChange={setDifficulty}
            />
          </div>

          {/* Prep, Cook, Servings */}
          <div className="grid grid-cols-4 gap-4">
            <Input
              label="Prep (min)"
              type="number"
              value={prepTime.toString()}
              onChange={(v) => setPrepTime(Number(v))}
            />
            <Input
              label="Cook (min)"
              type="number"
              value={cookTime.toString()}
              onChange={(v) => setCookTime(Number(v))}
            />
            <Input
              label="Min Servings"
              type="number"
              value={servingMin.toString()}
              onChange={(v) => setServingMin(Number(v))}
            />
            <Input
              label="Max Servings"
              type="number"
              value={servingMax?.toString() ?? ''}
              onChange={(v) => setServingMax(v ? Number(v) : undefined)}
              placeholder="Optional"
            />
          </div>

          {/* Additional Recipe Information */}
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Ethnicity/Cuisine"
              value={ethnicity}
              onChange={setEthnicity}
              placeholder="e.g., Italian, Mexican, etc."
            />
            <Input
              label="Oven Temperature (°F)"
              type="number"
              value={ovenTemperatureF?.toString() ?? ''}
              onChange={(v) => setOvenTemperatureF(v ? Number(v) : undefined)}
              placeholder="Optional"
            />
          </div>

          {/* Notes */}
          <div className="grid grid-cols-1 gap-4">
            <Input
              label="Notes"
              value={userNotes}
              onChange={setUserNotes}
              placeholder="Any additional notes about this recipe"
            />
          </div>

          {/* Ingredients List */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Ingredients</h2>
            {ingredients.map((ing, idx) => (
              <div key={idx} className="grid grid-cols-6 items-end gap-2">
                <Input
                  label={`Ingredient ${idx + 1}`}
                  className="col-span-2"
                  value={ing.name}
                  onChange={(v) => {
                    const list = [...ingredients];
                    list[idx] = { ...list[idx], name: v };
                    setIngredients(list);
                  }}
                  placeholder={`e.g., Onion`}
                />
                <Input
                  label="Qty"
                  type="number"
                  className="col-span-1"
                  value={ing.quantity_value?.toString() ?? ''}
                  onChange={(v) => {
                    const list = [...ingredients];
                    const val = v === '' ? undefined : Number(v);
                    list[idx] = { ...list[idx], quantity_value: val };
                    setIngredients(list);
                  }}
                  placeholder="1"
                />
                <Input
                  label="Unit"
                  className="col-span-1"
                  value={ing.quantity_unit ?? ''}
                  onChange={(v) => {
                    const list = [...ingredients];
                    list[idx] = { ...list[idx], quantity_unit: v };
                    setIngredients(list);
                  }}
                  placeholder="count, cup, g"
                />
                <Input
                  label="Method"
                  className="col-span-1"
                  value={ing.prep?.method ?? ''}
                  onChange={(v) => {
                    const list = [...ingredients];
                    list[idx] = {
                      ...list[idx],
                      prep: { ...(list[idx].prep || {}), method: v },
                    };
                    setIngredients(list);
                  }}
                  placeholder="chopped, sliced"
                />
                <Input
                  label="Size"
                  className="col-span-1"
                  value={ing.prep?.size_descriptor ?? ''}
                  onChange={(v) => {
                    const list = [...ingredients];
                    list[idx] = {
                      ...list[idx],
                      prep: { ...(list[idx].prep || {}), size_descriptor: v },
                    };
                    setIngredients(list);
                  }}
                  placeholder="small, medium, large"
                />
                {ingredients.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const list = [...ingredients];
                      list.splice(idx, 1);
                      setIngredients(list);
                    }}
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                setIngredients([
                  ...ingredients,
                  {
                    name: '',
                    quantity_value: undefined,
                    quantity_unit: '',
                    prep: {},
                    is_optional: false,
                  },
                ])
              }
            >
              + Add Ingredient
            </Button>
          </div>

          {/* Instructions List */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Instructions</h2>
            {instructions.map((step, idx) => (
              <div key={idx} className="flex items-center space-x-2">
                <Input
                  className="flex-1"
                  value={step}
                  onChange={(v) => {
                    const list = [...instructions];
                    list[idx] = v;
                    setInstructions(list);
                  }}
                  placeholder={`Step ${idx + 1}`}
                />
                {instructions.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const list = [...instructions];
                      list.splice(idx, 1);
                      setInstructions(list);
                    }}
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setInstructions([...instructions, ''])}
            >
              + Add Step
            </Button>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-2">
            {error && (
              <div className="mr-auto">
                <ErrorMessage message={error} />
              </div>
            )}
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate(`/recipes/${id}`)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isSubmitting}>
              {isSubmitting ? (
                <div className="flex items-center space-x-2">
                  <LoadingSpinner />
                  <span>Updating...</span>
                </div>
              ) : (
                'Update Recipe'
              )}
            </Button>
          </div>
        </form>
      </Card>
    </Container>
  );
};

export default RecipesEditPage;