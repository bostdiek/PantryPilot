import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
vi.mock('react-router-dom', () => ({ useNavigate: () => vi.fn() }));
vi.mock('../../components/ui/useToast', () => ({
  useToast: () => ({ success: vi.fn() }),
}));
vi.mock('../../hooks/usePasteSplit', () => ({
  usePasteSplit: () => ({
    pasteSplitModal: { isOpen: false, candidateSteps: [], originalContent: '' },
  }),
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
    vi.mock('../../stores/useRecipeStore', () => ({
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
    vi.mock('../../stores/useRecipeStore', () => ({
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
