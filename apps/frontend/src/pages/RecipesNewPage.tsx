import { useState, type FC, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
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
import {
  RECIPE_CATEGORIES,
  RECIPE_DIFFICULTIES,
  type RecipeCategory,
  type RecipeDifficulty,
} from '../types/Recipe';
import { saveRecipeOffline } from '../utils/offlineSync';
import { useApiHealth } from '../utils/useApiHealth';
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

const RecipesNewPage: FC = () => {
  const navigate = useNavigate();
  const { success } = useToast();
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
  const { addRecipe } = useRecipeStore();

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
      // Guard against invalid index
      if (targetIndex < 0 || targetIndex >= instructions.length) {
        console.warn(
          `Invalid target index ${targetIndex}, appending steps instead`
        );
        setInstructions((prev) => [
          ...prev,
          ...steps.filter((s) => s.trim() !== ''),
        ]);
        return;
      }

      const newInstructions = [...instructions];

      // If replaceEmpty is true and target step is empty, replace it
      if (replaceEmpty && newInstructions[targetIndex].trim() === '') {
        newInstructions.splice(
          targetIndex,
          1,
          ...steps.filter((s) => s.trim() !== '')
        );
      } else {
        // Insert steps after the current index
        newInstructions.splice(
          targetIndex + 1,
          0,
          ...steps.filter((s) => s.trim() !== '')
        );
      }

      setInstructions(newInstructions);
    },
    onReplaceStep: (targetIndex: number, content: string) => {
      // Guard against invalid index
      if (targetIndex < 0 || targetIndex >= instructions.length) {
        console.warn(
          `Invalid target index ${targetIndex}, cannot replace step`
        );
        return;
      }

      const newInstructions = [...instructions];
      newInstructions[targetIndex] = content;
      setInstructions(newInstructions);
    },
    getCurrentStepValue: (index: number) => {
      return instructions[index] || '';
    },
  });

  // Use the custom hook instead of direct useEffect
  const { isApiOnline } = useApiHealth();
  const apiUnavailable = !isApiOnline;

  // Check if there are unsaved changes
  const hasUnsavedChanges =
    title.trim() !== '' ||
    description.trim() !== '' ||
    prepTime > 0 ||
    cookTime > 0 ||
    ethnicity.trim() !== '' ||
    userNotes.trim() !== '' ||
    ingredients.some((ing) => ing.name.trim() !== '') ||
    instructions.some((inst) => inst.trim() !== '');

  // Block navigation if there are unsaved changes
  useUnsavedChanges(hasUnsavedChanges && !isSubmitting);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

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

    // If API is unavailable, store data locally and show message
    if (apiUnavailable) {
      try {
        const recipeData = {
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
        } as const;

        saveRecipeOffline(recipeData);

        setError(
          'API is currently unavailable. Your recipe has been saved locally and will be synced when connection is restored.'
        );
        setTimeout(() => navigate('/recipes'), 3000);
      } catch (err) {
        console.error('Failed to save recipe locally:', err);
        setError('Unable to save recipe. Please try again later.');
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    try {
      // Create the recipe data object matching the backend schema
      const recipeData = {
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

      // Use the store to add the recipe
      const result = await addRecipe(recipeData);

      if (result) {
        // Show success toast and navigate back to recipes list
        success('Recipe created successfully!');
        navigate('/recipes');
      } else {
        setError('Failed to create recipe. Please try again.');
      }
    } catch (err) {
      console.error('Failed to create recipe:', err);
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to create recipe. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Container size="md">
      <Card variant="default" className="mt-6 p-6">
        <h1 className="mb-4 text-2xl font-bold">Create New Recipe</h1>

        {apiUnavailable && (
          <div className="mb-4">
            <ErrorMessage message="⚠️ Backend service unavailable — recipe will be saved locally until connection is restored." />
          </div>
        )}

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
                  <div className="flex justify-end">
                    <button
                      type="button"
                      className="min-w-[44px] min-h-[44px] p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                      onClick={() => {
                        const list = [...ingredients];
                        list.splice(idx, 1);
                        setIngredients(list);
                      }}
                      aria-label={`Remove ingredient ${idx + 1}`}
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
              <div key={idx} className="flex items-start space-x-2">
                <div className="flex flex-col space-y-1 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      if (idx > 0) {
                        const list = [...instructions];
                        [list[idx], list[idx - 1]] = [list[idx - 1], list[idx]];
                        setInstructions(list);
                      }
                    }}
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
                    onClick={() => {
                      if (idx < instructions.length - 1) {
                        const list = [...instructions];
                        [list[idx], list[idx + 1]] = [list[idx + 1], list[idx]];
                        setInstructions(list);
                      }
                    }}
                    disabled={idx === instructions.length - 1}
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
                      onChange={(e) => {
                        const list = [...instructions];
                        list[idx] = e.target.value;
                        setInstructions(list);
                      }}
                      placeholder={`Describe step ${idx + 1}...`}
                      aria-label={`Step ${idx + 1}`}
                    />
                  </div>
                </div>

                {instructions.length > 1 && (
                  <div className="pt-7 flex justify-end">
                    {' '}
                    {/* Align with textarea top */}
                    <button
                      type="button"
                      className="min-w-[44px] min-h-[44px] p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                      onClick={() => {
                        const list = [...instructions];
                        list.splice(idx, 1);
                        setInstructions(list);
                      }}
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
              onClick={() => setInstructions([...instructions, ''])}
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
              onClick={() => navigate('/recipes')}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isSubmitting}>
              {isSubmitting ? (
                <div className="flex items-center space-x-2">
                  <LoadingSpinner />
                  <span>Saving...</span>
                </div>
              ) : (
                'Save Recipe'
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
};

export default RecipesNewPage;
