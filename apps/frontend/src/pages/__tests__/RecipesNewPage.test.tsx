import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// vi.mock factories are hoisted to the top of the file by Vitest's transform.
// Variables used inside those factories must be declared with vi.hoisted so
// they're initialised before the hoisted mock registrations run.
const createMealEntryMock = vi.hoisted(() => vi.fn());
const navigateMock = vi.hoisted(() => vi.fn());
const clearDuplicateMock = vi.hoisted(() => vi.fn());

// Mutable state shared between the hook mock and getState() so addRecipe can
// simulate setting duplicateInfo (as the real Zustand store does on 409).
const recipeStoreState = vi.hoisted(
  () =>
    ({
      duplicateInfo: null,
    }) as {
      duplicateInfo: {
        existing_recipe_id: string;
        similar_recipes: unknown[];
      } | null;
    }
);

// Basic stable mocks for modules used by the page
vi.mock('../../stores/useRecipeStore', () => ({
  useRecipeStore: () => ({
    addRecipe: vi.fn().mockResolvedValue(true),
    formSuggestion: null,
    isAISuggestion: false,
    clearFormSuggestion: vi.fn(),
  }),
}));

let apiOnline = true;
vi.mock('../../utils/useApiHealth', () => ({
  useApiHealth: () => ({ isApiOnline: apiOnline }),
}));
vi.mock('../../utils/offlineSync', () => ({ saveRecipeOffline: vi.fn() }));
vi.mock('../../hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: () => {},
}));
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));
vi.mock('../../components/ui/useToast', () => ({
  useToast: () => ({ success: vi.fn(), info: vi.fn() }),
}));
vi.mock('../../hooks/usePasteSplit', () => ({
  usePasteSplit: () => ({
    pasteSplitModal: { isOpen: false, candidateSteps: [], originalContent: '' },
  }),
}));
vi.mock('../../stores/useChatStore', () => ({
  useChatStore: Object.assign(() => ({}), {
    getState: () => ({ appendLocalAssistantMessage: vi.fn() }),
  }),
}));
vi.mock('../../utils/mealProposalStatus', () => ({
  markMealProposalSavedToBook: vi.fn(),
  markMealProposalAddedToPlan: vi.fn(),
}));
vi.mock('../../api/endpoints/recipes', () => ({
  getRecipeById: vi.fn().mockResolvedValue(null),
}));

// Shared AI suggestion used by tests that mock the recipe store
const suggestion = {
  title: 'Sug Title',
  description: 'Sug Desc',
  ingredients: [
    {
      name: 'Onion',
      quantity_value: 1,
      quantity_unit: 'count',
      prep: {},
      is_optional: false,
    },
  ],
  instructions: ['Do this'],
};

// Note: do not statically import RecipesNewPage here - tests import it after setting
// up module-level mocks to ensure fresh module state per test.

describe('RecipesNewPage (minimal)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiOnline = true;
    // Clear any persisted storage so AI suggestion doesn't leak between tests
    try {
      window.localStorage.clear();
      window.sessionStorage.clear();
    } catch {
      /* ignore */
    }
  });

  it('shows validation alert when submitting without ingredients', async () => {
    // Ensure we have a fresh module instance without any AI suggestion
    vi.resetModules();
    vi.doMock('../../stores/useRecipeStore', () => ({
      useRecipeStore: () => ({
        addRecipe: vi.fn().mockResolvedValue(true),
        formSuggestion: null,
        isAISuggestion: false,
        clearFormSuggestion: vi.fn(),
      }),
    }));

    const { default: FreshRecipesNewPage } = await import('../RecipesNewPage');
    render((<FreshRecipesNewPage />) as any);

    // If an AI suggestion banner leaked into this test, close it to restore default state
    const maybeClose = screen.queryByLabelText(/Close AI suggestion/i);
    if (maybeClose) {
      await userEvent.click(maybeClose);
    }

    const maybeIngredient = screen.queryByLabelText(/Ingredient 1/i);
    if (maybeIngredient) {
      await userEvent.clear(maybeIngredient);
    }
    const maybeStep = screen.queryByRole('textbox', { name: /Step 1/i });
    if (maybeStep) {
      await userEvent.clear(maybeStep);
    }

    // Ensure name present so browser won't block submit
    const name = screen.getByLabelText(/Recipe Name/i);
    await userEvent.type(name, 'Test');

    const save = screen.getByRole('button', { name: /save recipe/i });
    await userEvent.click(save);
    // The validation UI may render without a consistent role in some test envs;
    // assert the visible validation text appears instead.
    await waitFor(() =>
      expect(screen.getByText(/add at least one/i)).toBeTruthy()
    );
  });

  it('prefills fields when store provides AI suggestion', async () => {
    vi.resetModules();

    // use the module-scoped `suggestion` defined above
    vi.doMock('../../stores/useRecipeStore', () => ({
      useRecipeStore: () => ({
        addRecipe: vi.fn().mockResolvedValue(true),
        formSuggestion: suggestion,
        isAISuggestion: true,
        clearFormSuggestion: vi.fn(),
      }),
    }));

    const { default: RecipesNewPageWithMocks } =
      await import('../RecipesNewPage');
    render((<RecipesNewPageWithMocks />) as any);

    await waitFor(() =>
      expect(screen.getByDisplayValue('Sug Title')).toBeTruthy()
    );
    expect(screen.getByDisplayValue('Onion')).toBeTruthy();
    expect(screen.getByDisplayValue('Do this')).toBeTruthy();
  });
});

describe('RecipesNewPage - duplicate recipe handling', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    navigateMock.mockReset();
    clearDuplicateMock.mockReset();
    createMealEntryMock.mockReset();
    createMealEntryMock.mockResolvedValue({ id: 'meal-1' });
    recipeStoreState.duplicateInfo = null;
    try {
      window.localStorage.clear();
      window.sessionStorage.clear();
    } catch {
      /* ignore */
    }
  });

  it('proceeds with meal plan entry using existing_recipe_id when in assistant flow (409 duplicate)', async () => {
    // addRecipe simulates a 409: sets duplicateInfo in the shared store state
    // and returns null so the component reads duplicateInfo via getState().
    const addRecipeMock = vi.fn().mockImplementation(async () => {
      recipeStoreState.duplicateInfo = {
        existing_recipe_id: 'existing-uuid-123',
        similar_recipes: [],
      };
      return null;
    });

    vi.doMock('../../stores/useRecipeStore', () => {
      const useRecipeStore: any = () => ({
        addRecipe: addRecipeMock,
        formSuggestion: null,
        isAISuggestion: false,
        clearFormSuggestion: vi.fn(),
        duplicateInfo: null, // null on mount so the modal does not open immediately
        forceCreateRecipe: vi.fn(),
        clearDuplicateState: vi.fn(),
      });
      // getState() returns the live state so the submit handler sees the 409 duplicate info
      useRecipeStore.getState = () => recipeStoreState;
      return { useRecipeStore };
    });
    vi.doMock('../../api/endpoints/mealPlans', () => ({
      createMealEntry: createMealEntryMock,
    }));
    vi.doMock('react-router-dom', () => ({
      useNavigate: () => navigateMock,
      useSearchParams: () => [
        new URLSearchParams('proposalKey=test-key&mealPlanDate=2026-04-14'),
        vi.fn(),
      ],
    }));

    const { default: Page } = await import('../RecipesNewPage');
    render((<Page />) as any);

    // Fill required fields and submit
    await userEvent.type(screen.getByLabelText(/Recipe Name/i), 'Test Recipe');
    await userEvent.type(screen.getByLabelText(/Ingredient 1/i), 'Flour');
    await userEvent.type(
      screen.getByRole('textbox', { name: /Step 1/i }),
      'Mix everything'
    );
    await userEvent.click(screen.getByRole('button', { name: /save recipe/i }));

    // The submit handler should use the existing_recipe_id from the 409 response
    // to call createMealEntry, then navigate away.
    await waitFor(() => {
      expect(createMealEntryMock).toHaveBeenCalledWith(
        expect.objectContaining({
          recipeId: 'existing-uuid-123',
          plannedForDate: '2026-04-14',
        })
      );
    });
    expect(navigateMock).toHaveBeenCalled();
    // Duplicate modal should not be shown (auto-proceed path taken)
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('does not auto-proceed when NOT in assistant flow (no proposalKey, no mealPlanDate)', async () => {
    // addRecipe simulates a 409: sets duplicateInfo and returns null.
    const addRecipeMock = vi.fn().mockImplementation(async () => {
      recipeStoreState.duplicateInfo = {
        existing_recipe_id: 'existing-uuid-456',
        similar_recipes: [],
      };
      return null;
    });

    vi.doMock('../../stores/useRecipeStore', () => {
      const useRecipeStore: any = () => ({
        addRecipe: addRecipeMock,
        formSuggestion: null,
        isAISuggestion: false,
        clearFormSuggestion: vi.fn(),
        duplicateInfo: null,
        forceCreateRecipe: vi.fn(),
        clearDuplicateState: clearDuplicateMock,
      });
      useRecipeStore.getState = () => recipeStoreState;
      return { useRecipeStore };
    });
    vi.doMock('../../api/endpoints/mealPlans', () => ({
      createMealEntry: createMealEntryMock,
    }));
    vi.doMock('react-router-dom', () => ({
      useNavigate: () => navigateMock,
      // No proposalKey, no mealPlanDate → normal duplicate flow
      useSearchParams: () => [new URLSearchParams(), vi.fn()],
    }));

    const { default: Page } = await import('../RecipesNewPage');
    render((<Page />) as any);

    // Fill required fields and submit
    await userEvent.type(screen.getByLabelText(/Recipe Name/i), 'Test Recipe');
    await userEvent.type(screen.getByLabelText(/Ingredient 1/i), 'Flour');
    await userEvent.type(
      screen.getByRole('textbox', { name: /Step 1/i }),
      'Mix everything'
    );
    await userEvent.click(screen.getByRole('button', { name: /save recipe/i }));

    // Without assistant flow params, the auto-proceed path is NOT taken:
    // createMealEntry must not be called and the page must not navigate away.
    await waitFor(() => {
      expect(addRecipeMock).toHaveBeenCalled();
    });
    expect(createMealEntryMock).not.toHaveBeenCalled();
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
