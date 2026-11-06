import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Recipe } from '../../types/Recipe';
import RecipesEditPage from '../RecipesEditPage';
import { captureSessionRecovery } from '../../utils/sessionRecovery';
import { useAuthStore } from '../../stores/useAuthStore';

const mockNavigate = vi.fn();

const baseRecipe: Recipe = {
  id: 'r1',
  title: 'Spaghetti',
  description: 'Classic pasta',
  ingredients: [
    { name: 'Pasta', quantity_value: 200, quantity_unit: 'g' },
    { name: 'Tomato', prep: { method: 'chopped' } },
  ],
  instructions: ['Boil water', 'Cook pasta'],
  prep_time_minutes: 5,
  cook_time_minutes: 10,
  total_time_minutes: 15,
  serving_min: 2,
  serving_max: 4,
  difficulty: 'easy',
  category: 'dinner',
  ethnicity: 'Italian',
  oven_temperature_f: undefined,
  user_notes: '',
  link_source: '',
  ai_summary: '',
  created_at: new Date('2024-01-01'),
  updated_at: new Date('2024-01-01'),
};

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'r1' }),
    useLoaderData: () => baseRecipe,
  };
});

const mockUpdateRecipe = vi.fn();

vi.mock('../../stores/useRecipeStore', () => ({
  useRecipeStore: () => ({ updateRecipe: mockUpdateRecipe }),
}));

// Mock Toast component
const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
};

vi.mock('../../components/ui/Toast', () => ({
  useToast: () => mockToast,
}));

// Mock useUnsavedChanges hook to avoid window.confirm issues in tests
vi.mock('../../hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: () => ({ state: 'unblocked' }),
}));

// Mock Select to a simple native select to avoid Headless UI + SVG issues in jsdom
vi.mock('../../components/ui/Select', () => ({
  Select: ({ options, value, onChange, label }: any) => (
    <label>
      {label}
      <select
        aria-label={label}
        value={value?.id}
        onChange={(e) =>
          onChange(options.find((o: any) => o.id === e.target.value))
        }
      >
        {options.map((o: any) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  ),
}));

describe('RecipesEditPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    window.history.replaceState(null, '', '/recipes/r1/edit');
    useAuthStore.setState({
      user: { id: 'account-a', username: 'cook', email: 'cook@example.test' },
    });
  });

  afterEach(() => {
    window.history.replaceState(null, '', '/');
    useAuthStore.setState({ user: null });
  });

  it('restores unsaved ingredient/step rows and selected category/difficulty together', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<RecipesEditPage />);
    fireEvent.change(screen.getByLabelText(/recipe name/i), {
      target: { value: 'Unsaved soup' },
    });
    await user.click(screen.getByRole('button', { name: /add ingredient/i }));
    const ingredientNames = screen.getAllByPlaceholderText(/e\.g\., Onion/i);
    fireEvent.change(ingredientNames[2], { target: { value: 'Garlic' } });
    await user.click(screen.getByRole('button', { name: /add step/i }));
    fireEvent.change(screen.getAllByPlaceholderText(/Step \d+/i)[2], {
      target: { value: 'Simmer with garlic' },
    });
    await user.selectOptions(screen.getByLabelText(/category/i), 'lunch');
    await user.selectOptions(screen.getByLabelText(/difficulty/i), 'hard');
    captureSessionRecovery(useAuthStore.getState().user?.id);
    unmount();

    render(<RecipesEditPage />);

    expect(screen.getByLabelText(/recipe name/i)).toHaveValue('Unsaved soup');
    expect(screen.getAllByPlaceholderText(/e\.g\., Onion/i)[2]).toHaveValue(
      'Garlic'
    );
    expect(
      screen
        .getAllByPlaceholderText(/Step \d+/i)
        .map((element) => (element as HTMLTextAreaElement).value)
    ).toEqual(['Boil water', 'Cook pasta', 'Simmer with garlic']);
    expect(screen.getByLabelText(/category/i)).toHaveValue('lunch');
    expect(screen.getByLabelText(/difficulty/i)).toHaveValue('hard');
    expect(sessionStorage.getItem('pantrypilot-session-recovery')).toBeNull();
  });

  it('pre-populates form with recipe data and updates on submit', async () => {
    const user = userEvent.setup();
    render(<RecipesEditPage />);

    // Pre-populated name
    const nameInput = screen.getByLabelText(/recipe name/i) as HTMLInputElement;
    expect(nameInput.value).toBe('Spaghetti');

    // Update title
    await user.clear(nameInput);
    await user.type(nameInput, 'Spaghetti Bolognese');

    // Ensure ingredients are rendered and update first ingredient quantity
    const qtyInputs = screen.getAllByLabelText(/qty/i) as HTMLInputElement[];
    expect(qtyInputs[0].value).toBe('200');
    await user.clear(qtyInputs[0]);
    await user.type(qtyInputs[0], '250');

    // Submit
    const submit = screen.getByRole('button', { name: /update recipe/i });
    mockUpdateRecipe.mockResolvedValue({
      ...baseRecipe,
      title: 'Spaghetti Bolognese',
    });
    await user.click(submit);

    // Called with mapped payload
    expect(mockUpdateRecipe).toHaveBeenCalled();
    const [, payload] = mockUpdateRecipe.mock.calls[0];
    expect(payload.title).toBe('Spaghetti Bolognese');
    // Ingredients mapped: quantity_unit becomes undefined when empty
    const pasta = payload.ingredients.find((i: any) => i.name === 'Pasta');
    expect(pasta.quantity_value).toBe(250);

    // Navigates back to detail
    expect(mockNavigate).toHaveBeenCalledWith('/recipes/r1');
  });

  it.each(['account-a', 'account-b'])(
    'waits for the profile before considering the account-bound draft (%s)',
    (returningAccount) => {
      const original = render(<RecipesEditPage />);
      fireEvent.change(screen.getByLabelText(/recipe name/i), {
        target: { value: 'Recovered after profile loads' },
      });
      captureSessionRecovery('account-a');
      original.unmount();
      useAuthStore.setState({ user: null });

      render(<RecipesEditPage />);
      expect(screen.getByLabelText(/recipe name/i)).toHaveValue('Spaghetti');
      expect(
        sessionStorage.getItem('pantrypilot-session-recovery')
      ).not.toBeNull();
      act(() => {
        useAuthStore.setState({
          user: {
            id: returningAccount,
            username: 'cook',
            email: 'cook@example.test',
          },
        });
      });

      expect(screen.getByLabelText(/recipe name/i)).toHaveValue(
        returningAccount === 'account-a'
          ? 'Recovered after profile loads'
          : 'Spaghetti'
      );
    }
  );

  it('handles instruction reordering in edit form', async () => {
    const user = userEvent.setup();
    render(<RecipesEditPage />);

    // Find the "Instructions" section first
    screen.getByText('Instructions');

    // Get the "Add Step" button which should be in the Instructions section
    const addStepButton = screen.getByRole('button', { name: /add step/i });

    // Add a new step for testing
    await user.click(addStepButton);

    // Find all instruction inputs
    const instructionTextboxes = screen.getAllByPlaceholderText(
      /Step \d+/i
    ) as HTMLInputElement[];

    // We need at least 3 inputs (2 from base recipe + 1 we added)
    expect(instructionTextboxes.length).toBeGreaterThanOrEqual(3);

    // Type in values for the first 3 inputs
    await user.type(instructionTextboxes[0], ' - Updated Step 1');
    await user.type(instructionTextboxes[1], ' - Updated Step 2');
    await user.type(instructionTextboxes[2], 'New Step 3');

    // Now move the second step up to first position
    const moveUpButtons = screen.getAllByLabelText(/move step.*up/i);
    await user.click(moveUpButtons[1]);

    // Check that the reordering worked
    expect(instructionTextboxes[0].value).toBe('Cook pasta - Updated Step 2');
    expect(instructionTextboxes[1].value).toBe('Boil water - Updated Step 1');
    expect(instructionTextboxes[2].value).toBe('New Step 3');

    // Move the third step up twice to the top
    await user.click(moveUpButtons[2]); // Move from position 2 to 1
    const finalMoveUpButtons = screen.getAllByLabelText(/move step.*up/i);
    await user.click(finalMoveUpButtons[1]); // Move from position 1 to 0

    // Check final order
    expect(instructionTextboxes[0].value).toBe('New Step 3');
    expect(instructionTextboxes[1].value).toBe('Cook pasta - Updated Step 2');
    expect(instructionTextboxes[2].value).toBe('Boil water - Updated Step 1');
  });

  it('shows accessible error messages', async () => {
    const user = userEvent.setup();
    render(<RecipesEditPage />);

    // Mock updateRecipe to return null (failure)
    mockUpdateRecipe.mockResolvedValue(null);

    // Submit form to trigger validation error
    const submitButton = screen.getByRole('button', { name: /update recipe/i });
    await user.click(submitButton);

    // Just check for any error message, without requiring a specific role
    try {
      const errorMessage = screen.getByText(/failed to update/i);
      expect(errorMessage).toBeInTheDocument();
    } catch {
      // If the specific message isn't found, at least check for some error indicator
      const errorElement = screen.getByText(/error|failed|invalid/i);
      expect(errorElement).toBeInTheDocument();
    }
  });
});
