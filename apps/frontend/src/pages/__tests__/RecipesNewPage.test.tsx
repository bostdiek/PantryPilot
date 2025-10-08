import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mocks for modules used by the page. These MUST be declared before importing the page
vi.mock('../../stores/useRecipeStore', () => ({
  useRecipeStore: () => ({
    addRecipe: vi.fn().mockResolvedValue(true),
    formSuggestion: null,
    isAISuggestion: false,
    clearFormSuggestion: vi.fn(),
  }),
}));

// Allow tests to toggle API online state
let apiOnline = true;
vi.mock('../../utils/useApiHealth', () => ({
  useApiHealth: () => ({ isApiOnline: apiOnline }),
}));

vi.mock('../../utils/offlineSync', () => ({
  saveRecipeOffline: vi.fn(),
}));

vi.mock('../../hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: () => {},
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock('../../components/ui/useToast', () => ({
  useToast: () => ({ success: vi.fn() }),
}));

vi.mock('../../hooks/usePasteSplit', () => ({
  usePasteSplit: () => ({
    pasteSplitModal: { isOpen: false, candidateSteps: [], originalContent: '' },
    handleInstructionPaste: vi.fn(),
    handlePasteSplitConfirm: vi.fn(),
    handlePasteAsSingle: vi.fn(),
    handlePasteSplitCancel: vi.fn(),
    closePasteSplitModal: vi.fn(),
  }),
}));

import RecipesNewPage from '../RecipesNewPage';

describe('RecipesNewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form and client-side validation prevents submit when no ingredient/instruction', async () => {
    render(<RecipesNewPage />);

    // Fill the required recipe name so HTML validation does not block submit
    const nameInput = screen.getByLabelText(/Recipe Name/i);
    await userEvent.type(nameInput, 'Test Recipe');

    // Click Save
    await userEvent.click(screen.getByRole('button', { name: /save recipe/i }));

    // Expect validation error about ingredient or instruction
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('alert')).toHaveTextContent(
      /Please add at least one/
    );
  });

  it('adds and removes ingredient and instruction rows', async () => {
    render(<RecipesNewPage />);

    // Add an ingredient
    await userEvent.click(
      screen.getByRole('button', { name: /\+ add ingredient/i })
    );
    // There should now be an input for Ingredient 2 (use role to avoid matching buttons)
    expect(
      screen.getByRole('textbox', { name: /Ingredient 2/i })
    ).toBeInTheDocument();

    // Remove second ingredient (button has aria-label)
    const removeButtons = screen.getAllByLabelText(/Remove ingredient/i);
    expect(removeButtons.length).toBeGreaterThanOrEqual(1);
    await userEvent.click(removeButtons[0]);

    // Add an instruction
    await userEvent.click(screen.getByRole('button', { name: /\+ add step/i }));
    expect(
      screen.getByRole('textbox', { name: /Step 2/i })
    ).toBeInTheDocument();

    // Remove the new step
    const removeStepButtons = screen.getAllByLabelText(/Remove step/i);
    await userEvent.click(removeStepButtons[0]);
    expect(
      screen.queryByRole('textbox', { name: /Step 2/i })
    ).not.toBeInTheDocument();
  });

  it('saves recipe offline when API is unavailable', async () => {
    // Make API unavailable by toggling the mocked apiOnline variable
    apiOnline = false;
    const offlineModule = await import('../../utils/offlineSync');
    const saveRecipeOffline = offlineModule.saveRecipeOffline as any;

    render(<RecipesNewPage />);

    // Fill minimal valid data: add ingredient name and instruction
    const nameInput = screen.getByLabelText(/Recipe Name/i);
    await userEvent.type(nameInput, 'Test Recipe');

    const ingredientInput = screen.getByRole('textbox', {
      name: /Ingredient 1/i,
    });
    await userEvent.type(ingredientInput, 'Flour');

    const stepInput = screen.getByRole('textbox', { name: /Step 1/i });
    await userEvent.type(stepInput, 'Mix');

    // Submit
    await userEvent.click(screen.getByRole('button', { name: /save recipe/i }));

    await waitFor(() => expect(saveRecipeOffline).toHaveBeenCalled());
    apiOnline = true; // reset
  });
});
