import { useReducer, useState, type FC, type FormEvent } from 'react';
import { useLoaderData, useNavigate, useParams } from 'react-router-dom';
import { PasteSplitModal } from '../components/recipes/PasteSplitModal';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Icon } from '../components/ui/Icon';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select, type SelectOption } from '../components/ui/Select';
import { Textarea } from '../components/ui/Textarea';
import { useToast } from '../components/ui/useToast';
import { usePasteSplit } from '../hooks/usePasteSplit';
import { useUnsavedChanges } from '../hooks/useUnsavedChanges';
import { useRecipeStore } from '../stores/useRecipeStore';
import type { Ingredient } from '../types/Ingredients';
import type { Recipe } from '../types/Recipe';
import {
  RECIPE_CATEGORIES,
  RECIPE_DIFFICULTIES,
  type RecipeCategory,
  type RecipeDifficulty,
} from '../types/Recipe';
import {
  mapIngredientsForApi,
  normalizeIngredientsForForm,
} from '../utils/ingredients';
import TrashIcon from '../components/ui/icons/trash.svg?react';

// Create options for the Select component
const categoryOptions: SelectOption[] = RECIPE_CATEGORIES.map((cat) => ({
  id: cat,
  name: cat.charAt(0).toUpperCase() + cat.slice(1), // Capitalize first letter
}));

const difficultyOptions: SelectOption[] = RECIPE_DIFFICULTIES.map((diff) => ({
  id: diff,
  name: diff.charAt(0).toUpperCase() + diff.slice(1), // Capitalize first letter
}));

type RecipeEditFormProps = { recipe: Recipe };

function RecipeEditForm({ recipe }: RecipeEditFormProps) {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { updateRecipe } = useRecipeStore();
  const { success } = useToast();

  type FormState = {
    title: string;
    description: string;
    category: SelectOption;
    difficulty: SelectOption;
    prepTime: number;
    cookTime: number;
    servingMin: number;
    servingMax?: number;
    ethnicity: string;
    ovenTemperatureF?: number;
    userNotes: string;
    ingredients: Ingredient[];
    instructions: string[];
  };

  type Action =
    | { type: 'SET_FIELD'; field: keyof FormState; value: any }
    | { type: 'SET_INGREDIENT'; index: number; value: Partial<Ingredient> }
    | { type: 'ADD_INGREDIENT' }
    | { type: 'REMOVE_INGREDIENT'; index: number }
    | { type: 'SET_INSTRUCTION'; index: number; value: string }
    | { type: 'ADD_INSTRUCTION' }
    | { type: 'REMOVE_INSTRUCTION'; index: number }
    | { type: 'MOVE_INSTRUCTION_UP'; index: number }
    | { type: 'MOVE_INSTRUCTION_DOWN'; index: number }
    | {
        type: 'INSERT_INSTRUCTIONS_AT';
        index: number;
        steps: string[];
        replaceEmpty?: boolean;
      };

  function reducer(state: FormState, action: Action): FormState {
    switch (action.type) {
      case 'SET_FIELD':
        return { ...state, [action.field]: action.value } as FormState;
      case 'SET_INGREDIENT': {
        const next = [...state.ingredients];
        next[action.index] = { ...next[action.index], ...action.value };
        return { ...state, ingredients: next };
      }
      case 'ADD_INGREDIENT':
        return {
          ...state,
          ingredients: [
            ...state.ingredients,
            {
              name: '',
              quantity_value: undefined,
              quantity_unit: '',
              prep: {},
              is_optional: false,
            },
          ],
        };
      case 'REMOVE_INGREDIENT': {
        const next = [...state.ingredients];
        next.splice(action.index, 1);
        return {
          ...state,
          ingredients: next.length ? next : normalizeIngredientsForForm([]),
        };
      }
      case 'SET_INSTRUCTION': {
        const next = [...state.instructions];
        next[action.index] = action.value;
        return { ...state, instructions: next };
      }
      case 'ADD_INSTRUCTION':
        return { ...state, instructions: [...state.instructions, ''] };
      case 'REMOVE_INSTRUCTION': {
        const next = [...state.instructions];
        next.splice(action.index, 1);
        return { ...state, instructions: next.length ? next : [''] };
      }
      case 'MOVE_INSTRUCTION_UP': {
        if (action.index > 0) {
          const next = [...state.instructions];
          [next[action.index], next[action.index - 1]] = [
            next[action.index - 1],
            next[action.index],
          ];
          return { ...state, instructions: next };
        }
        return state;
      }
      case 'MOVE_INSTRUCTION_DOWN': {
        if (action.index < state.instructions.length - 1) {
          const next = [...state.instructions];
          [next[action.index], next[action.index + 1]] = [
            next[action.index + 1],
            next[action.index],
          ];
          return { ...state, instructions: next };
        }
        return state;
      }
      case 'INSERT_INSTRUCTIONS_AT': {
        const next = [...state.instructions];
        const { index, steps, replaceEmpty } = action;

        // Guard against invalid index
        if (index < 0 || index >= next.length) {
          console.warn(
            `Invalid instruction index ${index}, appending steps instead`
          );
          return {
            ...state,
            instructions: [...next, ...steps.filter((s) => s.trim() !== '')],
          };
        }

        // If replaceEmpty is true and target step is empty, replace it
        if (replaceEmpty && next[index].trim() === '') {
          next.splice(index, 1, ...steps.filter((s) => s.trim() !== ''));
        } else {
          // Insert steps after the target index
          next.splice(index + 1, 0, ...steps.filter((s) => s.trim() !== ''));
        }

        return { ...state, instructions: next };
      }
      default:
        return state;
    }
  }

  const [form, dispatch] = useReducer(
    reducer,
    undefined as unknown as FormState,
    () => ({
      title: recipe.title,
      description: recipe.description || '',
      category:
        categoryOptions.find((c) => c.id === recipe.category) ||
        categoryOptions[0],
      difficulty:
        difficultyOptions.find((d) => d.id === recipe.difficulty) ||
        difficultyOptions[0],
      prepTime: recipe.prep_time_minutes || 0,
      cookTime: recipe.cook_time_minutes || 0,
      servingMin: recipe.serving_min || 1,
      servingMax: recipe.serving_max || undefined,
      ethnicity: recipe.ethnicity || '',
      ovenTemperatureF: recipe.oven_temperature_f || undefined,
      userNotes: recipe.user_notes || '',
      ingredients: normalizeIngredientsForForm(recipe.ingredients),
      instructions:
        recipe.instructions && recipe.instructions.length > 0
          ? recipe.instructions
          : [''],
    })
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Shared paste handling hook
  const {
    pasteSplitModal,
    handleInstructionPaste,
    handlePasteSplitConfirm,
    handlePasteAsSingle,
    handlePasteSplitCancel,
    closePasteSplitModal,
  } = usePasteSplit({
    onInsertSteps: (
      targetIndex: number,
      steps: string[],
      replaceEmpty?: boolean
    ) => {
      // Guard against invalid index with bounds checking
      if (targetIndex < 0 || targetIndex >= form.instructions.length) {
        console.warn(
          `Invalid target index ${targetIndex}, appending steps instead`
        );
        dispatch({
          type: 'INSERT_INSTRUCTIONS_AT',
          index: form.instructions.length - 1,
          steps,
        });
        return;
      }

      dispatch({
        type: 'INSERT_INSTRUCTIONS_AT',
        index: targetIndex,
        steps,
        replaceEmpty,
      });
    },
    onReplaceStep: (targetIndex: number, content: string) => {
      // Guard against invalid index
      if (targetIndex < 0 || targetIndex >= form.instructions.length) {
        console.warn(
          `Invalid target index ${targetIndex}, cannot replace step`
        );
        return;
      }

      dispatch({ type: 'SET_INSTRUCTION', index: targetIndex, value: content });
    },
    getCurrentStepValue: (index: number) => {
      return form.instructions[index] || '';
    },
  });

  // Check if there are unsaved changes by comparing current form state with original recipe
  const hasUnsavedChanges =
    form.title !== recipe.title ||
    form.description !== (recipe.description || '') ||
    form.category.id !== recipe.category ||
    form.difficulty.id !== recipe.difficulty ||
    form.prepTime !== (recipe.prep_time_minutes || 0) ||
    form.cookTime !== (recipe.cook_time_minutes || 0) ||
    form.servingMin !== (recipe.serving_min || 1) ||
    form.servingMax !== recipe.serving_max ||
    form.ethnicity !== (recipe.ethnicity || '') ||
    form.ovenTemperatureF !== recipe.oven_temperature_f ||
    form.userNotes !== (recipe.user_notes || '') ||
    JSON.stringify(form.ingredients) !==
      JSON.stringify(normalizeIngredientsForForm(recipe.ingredients)) ||
    JSON.stringify(form.instructions) !==
      JSON.stringify(recipe.instructions || ['']);

  // Block navigation if there are unsaved changes
  useUnsavedChanges(hasUnsavedChanges && !isSubmitting);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!id) {
      setError('Recipe ID is missing');
      return;
    }

    // Clear previous errors
    setError(null);
    setIsSubmitting(true);

    // Filter out empty instructions and ingredients
    const filteredInstructions = form.instructions.filter(
      (step) => step.trim() !== ''
    );
    const filteredIngredients = form.ingredients.filter(
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
        title: form.title,
        description: form.description,
        category: form.category.id as RecipeCategory,
        difficulty: form.difficulty.id as RecipeDifficulty,
        prep_time_minutes: form.prepTime,
        cook_time_minutes: form.cookTime,
        serving_min: form.servingMin,
        serving_max: form.servingMax,
        ethnicity: form.ethnicity || undefined,
        oven_temperature_f: form.ovenTemperatureF,
        user_notes: form.userNotes || undefined,
        instructions: filteredInstructions,
        ingredients: mapIngredientsForApi(filteredIngredients),
      };

      // Use the store to update the recipe
      const result = await updateRecipe(id, recipeUpdateData);

      if (result) {
        // Show success toast and navigate back to the recipe detail page
        success('Recipe updated successfully!');
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
            value={form.title}
            onChange={(v) =>
              dispatch({ type: 'SET_FIELD', field: 'title', value: v })
            }
            placeholder="Enter recipe name"
            required
          />
          <Input
            label="Description"
            value={form.description}
            onChange={(v) =>
              dispatch({ type: 'SET_FIELD', field: 'description', value: v })
            }
            placeholder="Brief description of the recipe"
          />

          {/* Category and Difficulty */}
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Category"
              options={categoryOptions}
              value={form.category}
              onChange={(v) =>
                dispatch({ type: 'SET_FIELD', field: 'category', value: v })
              }
            />

            <Select
              label="Difficulty"
              options={difficultyOptions}
              value={form.difficulty}
              onChange={(v) =>
                dispatch({ type: 'SET_FIELD', field: 'difficulty', value: v })
              }
            />
          </div>

          {/* Prep, Cook, Servings */}
          <div className="grid grid-cols-4 gap-4">
            <Input
              label="Prep (min)"
              type="number"
              value={form.prepTime.toString()}
              onChange={(v) =>
                dispatch({
                  type: 'SET_FIELD',
                  field: 'prepTime',
                  value: Number(v),
                })
              }
            />
            <Input
              label="Cook (min)"
              type="number"
              value={form.cookTime.toString()}
              onChange={(v) =>
                dispatch({
                  type: 'SET_FIELD',
                  field: 'cookTime',
                  value: Number(v),
                })
              }
            />
            <Input
              label="Min Servings"
              type="number"
              value={form.servingMin.toString()}
              onChange={(v) =>
                dispatch({
                  type: 'SET_FIELD',
                  field: 'servingMin',
                  value: Number(v),
                })
              }
            />
            <Input
              label="Max Servings"
              type="number"
              value={form.servingMax?.toString() ?? ''}
              onChange={(v) =>
                dispatch({
                  type: 'SET_FIELD',
                  field: 'servingMax',
                  value: v ? Number(v) : undefined,
                })
              }
              placeholder="Optional"
            />
          </div>

          {/* Additional Recipe Information */}
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Ethnicity/Cuisine"
              value={form.ethnicity}
              onChange={(v) =>
                dispatch({ type: 'SET_FIELD', field: 'ethnicity', value: v })
              }
              placeholder="e.g., Italian, Mexican, etc."
            />
            <Input
              label="Oven Temperature (°F)"
              type="number"
              value={form.ovenTemperatureF?.toString() ?? ''}
              onChange={(v) =>
                dispatch({
                  type: 'SET_FIELD',
                  field: 'ovenTemperatureF',
                  value: v ? Number(v) : undefined,
                })
              }
              placeholder="Optional"
            />
          </div>

          {/* Notes */}
          <div className="grid grid-cols-1 gap-4">
            <Input
              label="Notes"
              value={form.userNotes}
              onChange={(v) =>
                dispatch({ type: 'SET_FIELD', field: 'userNotes', value: v })
              }
              placeholder="Any additional notes about this recipe"
            />
          </div>

          {/* Ingredients List */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Ingredients</h2>
            {form.ingredients.map((ing, idx) => (
              <div key={idx} className="flex items-end justify-between gap-4">
                <div className="grid grid-cols-6 items-end gap-2 flex-1">
                  <Input
                    label={`Ingredient ${idx + 1}`}
                    className="col-span-2"
                    value={ing.name}
                    onChange={(v) =>
                      dispatch({
                        type: 'SET_INGREDIENT',
                        index: idx,
                        value: { name: v },
                      })
                    }
                    placeholder={`e.g., Onion`}
                  />
                  <Input
                    label="Qty"
                    type="number"
                    className="col-span-1"
                    value={ing.quantity_value?.toString() ?? ''}
                    onChange={(v) =>
                      dispatch({
                        type: 'SET_INGREDIENT',
                        index: idx,
                        value: {
                          quantity_value: v === '' ? undefined : Number(v),
                        },
                      })
                    }
                    placeholder="1"
                  />
                  <Input
                    label="Unit"
                    className="col-span-1"
                    value={ing.quantity_unit ?? ''}
                    onChange={(v) =>
                      dispatch({
                        type: 'SET_INGREDIENT',
                        index: idx,
                        value: { quantity_unit: v },
                      })
                    }
                    placeholder="count, cup, g"
                  />
                  <Input
                    label="Method"
                    className="col-span-1"
                    value={ing.prep?.method ?? ''}
                    onChange={(v) =>
                      dispatch({
                        type: 'SET_INGREDIENT',
                        index: idx,
                        value: { prep: { ...(ing.prep || {}), method: v } },
                      })
                    }
                    placeholder="chopped, sliced"
                  />
                  <Input
                    label="Size"
                    className="col-span-1"
                    value={ing.prep?.size_descriptor ?? ''}
                    onChange={(v) =>
                      dispatch({
                        type: 'SET_INGREDIENT',
                        index: idx,
                        value: {
                          prep: { ...(ing.prep || {}), size_descriptor: v },
                        },
                      })
                    }
                    placeholder="small, medium, large"
                  />
                </div>
                {form.ingredients.length > 1 && (
                  <button
                    type="button"
                    className="min-w-[44px] min-h-[44px] p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
                    onClick={() =>
                      dispatch({ type: 'REMOVE_INGREDIENT', index: idx })
                    }
                    aria-label={`Remove ingredient ${idx + 1}`}
                  >
                    <Icon svg={TrashIcon} className="h-5 w-5" />
                  </button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => dispatch({ type: 'ADD_INGREDIENT' })}
            >
              + Add Ingredient
            </Button>
          </div>

          {/* Instructions List */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Instructions</h2>
            {form.instructions.map((step, idx) => (
              <div key={idx} className="flex items-start space-x-2">
                <div className="flex flex-col space-y-1 pt-2">
                  <button
                    type="button"
                    onClick={() =>
                      dispatch({ type: 'MOVE_INSTRUCTION_UP', index: idx })
                    }
                    disabled={idx === 0}
                    className="p-1 text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-30"
                    aria-label={`Move step ${idx + 1} up`}
                  >
                    <svg
                      className="h-4 w-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      dispatch({ type: 'MOVE_INSTRUCTION_DOWN', index: idx })
                    }
                    disabled={idx === form.instructions.length - 1}
                    className="p-1 text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-30"
                    aria-label={`Move step ${idx + 1} down`}
                  >
                    <svg
                      className="h-4 w-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                </div>

                {/* Constrained reading width for better typography */}
                <div className="mx-auto max-w-prose flex-1">
                  <div className="space-y-1">
                    <label
                      className="block text-sm font-medium text-gray-700"
                      htmlFor={`step-${idx}`}
                    >
                      Step {idx + 1}
                    </label>
                    <Textarea
                      id={`step-${idx}`}
                      value={step}
                      rows={3}
                      maxLength={1000} // reasonable limit for individual steps
                      onPaste={(e) => handleInstructionPaste(e, idx)}
                      onChange={(e) =>
                        dispatch({
                          type: 'SET_INSTRUCTION',
                          index: idx,
                          value: e.target.value,
                        })
                      }
                      placeholder={`Describe step ${idx + 1}...`}
                      aria-label={`Step ${idx + 1}`}
                    />
                  </div>
                </div>

                {form.instructions.length > 1 && (
                  <div className="pt-7 flex justify-end">
                    {' '}
                    {/* Align with textarea top */}
                    <button
                      type="button"
                      className="min-w-[44px] min-h-[44px] p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                      onClick={() =>
                        dispatch({ type: 'REMOVE_INSTRUCTION', index: idx })
                      }
                      aria-label={`Remove step ${idx + 1}`}
                    >
                      <Icon svg={TrashIcon} className="h-5 w-5" />
                    </button>
                  </div>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => dispatch({ type: 'ADD_INSTRUCTION' })}
            >
              + Add Step
            </Button>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-2">
            {error && (
              <div className="mr-auto" role="alert" aria-live="polite">
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

        {/* Paste Split Modal */}
        <PasteSplitModal
          isOpen={pasteSplitModal.isOpen}
          onClose={closePasteSplitModal}
          onConfirm={handlePasteSplitConfirm}
          onCancel={handlePasteSplitCancel}
          onPasteAsSingle={handlePasteAsSingle}
          candidateSteps={pasteSplitModal.candidateSteps}
          originalContent={pasteSplitModal.originalContent}
        />
      </Card>
    </Container>
  );
}

const RecipesEditPage: FC = () => {
  const recipe = useLoaderData() as Recipe | null;

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

  return <RecipeEditForm recipe={recipe} />;
};

export default RecipesEditPage;
