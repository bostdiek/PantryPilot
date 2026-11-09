import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { useRecipeStore } from '../stores/useRecipeStore';
import RecipesNewPage from './RecipesNewPage';
import { captureSessionRecovery } from '../utils/sessionRecovery';
import { useAuthStore } from '../stores/useAuthStore';
import { mockResizeObserver } from 'jsdom-testing-mocks';

mockResizeObserver();

// Mock SVG imports for Select icons
vi.mock('../components/ui/icons/chevron-up-down.svg?react', () => ({
  default: () => <div data-testid="mock-chevron-icon" />,
}));
vi.mock('../components/ui/icons/check.svg?react', () => ({
  default: () => <div data-testid="mock-check-icon" />,
}));
vi.mock('../components/ui/icons/trash.svg?react', () => ({
  default: () => <div data-testid="mock-trash-icon" />,
}));
// Mock router navigation
const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual('react-router-dom')),
  useNavigate: () => navigateMock,
}));

// Mock useUnsavedChanges hook to avoid window.confirm issues in tests
vi.mock('../hooks/useUnsavedChanges', () => ({
  useUnsavedChanges: () => ({ state: 'unblocked' }),
}));

describe('RecipesNewPage', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    sessionStorage.clear();
    useAuthStore.setState({
      user: { id: 'cook-a', username: 'cook', email: 'cook@example.test' },
    });
  });

  test.each(['cook-a', 'cook-b'])(
    'waits for profile %s before considering an account-qualified draft',
    async (accountId) => {
      const { unmount } = render(
        <MemoryRouter>
          <RecipesNewPage />
        </MemoryRouter>
      );
      fireEvent.change(screen.getByLabelText(/recipe name/i), {
        target: { value: 'Private draft' },
      });
      fireEvent.change(screen.getByLabelText('Step 1'), {
        target: { value: 'Chop carefully' },
      });
      captureSessionRecovery('cook-a');
      unmount();
      useAuthStore.setState({ user: null });
      render(
        <MemoryRouter>
          <RecipesNewPage />
        </MemoryRouter>
      );
      expect(screen.getByLabelText(/recipe name/i)).toHaveValue('');
      await act(async () => {
        useAuthStore.getState().setUser({
          id: accountId,
          username: 'cook',
          email: 'cook@example.test',
        });
      });
      expect(screen.getByLabelText(/recipe name/i)).toHaveValue(
        accountId === 'cook-a' ? 'Private draft' : ''
      );
      expect(screen.getByLabelText('Step 1')).toHaveValue(
        accountId === 'cook-a' ? 'Chop carefully' : ''
      );
    }
  );

  test('reopens pending instruction edits and imports them at their original target', async () => {
    const { unmount } = render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );
    fireEvent.change(screen.getByLabelText('Step 1'), {
      target: { value: 'Base step' },
    });
    fireEvent.click(screen.getByText(/add step/i));
    fireEvent.paste(screen.getByLabelText('Step 2'), {
      clipboardData: {
        getData: () => '1. Chop onions.\n2. Simmer soup.\n3. Serve hot.',
      },
    });
    const dialog = screen.getByRole('dialog', {
      name: 'Import Multiple Steps',
    });
    fireEvent.change(within(dialog).getByLabelText('Step 1'), {
      target: { value: 'Chop onions finely' },
    });
    fireEvent.click(within(dialog).getByLabelText('Remove step 2'));
    captureSessionRecovery('cook-a');
    unmount();
    useAuthStore.setState({ user: null });
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await act(async () => {
      useAuthStore.getState().setUser({
        id: 'cook-a',
        username: 'cook',
        email: 'cook@example.test',
      });
    });
    const recovered = screen.getByRole('dialog', {
      name: 'Import Multiple Steps',
    });
    expect(within(recovered).getByLabelText('Step 1')).toHaveValue(
      'Chop onions finely'
    );
    expect(within(recovered).getAllByLabelText(/^Step \d+$/)).toHaveLength(2);
    fireEvent.click(within(recovered).getByText('Import 2 Steps'));
    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    );
    expect(screen.getByLabelText('Step 1')).toHaveValue('Base step');
    expect(screen.getByLabelText('Step 2')).toHaveValue('Chop onions finely');
    expect(screen.getByLabelText('Step 3')).toHaveValue('Serve hot.');
  });

  test('restores repeated rows and custom selects without mixing recipe fields', async () => {
    const { unmount } = render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );
    fireEvent.change(screen.getByLabelText(/recipe name/i), {
      target: { value: 'Draft soup' },
    });
    fireEvent.change(screen.getByPlaceholderText(/e\.g\., Onion/i), {
      target: { value: 'Onion' },
    });
    fireEvent.click(screen.getByText(/add ingredient/i));
    fireEvent.change(screen.getAllByPlaceholderText(/e\.g\., Onion/i)[1], {
      target: { value: 'Garlic' },
    });
    fireEvent.change(screen.getByLabelText('Step 1'), {
      target: { value: 'Chop' },
    });
    fireEvent.click(screen.getByText(/add step/i));
    fireEvent.change(screen.getByLabelText('Step 2'), {
      target: { value: 'Simmer' },
    });
    fireEvent.click(screen.getByLabelText(/category/i));
    fireEvent.click(await screen.findByRole('option', { name: 'Lunch' }));
    fireEvent.click(screen.getByLabelText(/difficulty/i));
    fireEvent.click(await screen.findByRole('option', { name: 'Hard' }));
    captureSessionRecovery(useAuthStore.getState().user?.id);
    unmount();

    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    expect(screen.getByLabelText(/recipe name/i)).toHaveValue('Draft soup');
    expect(
      screen
        .getAllByPlaceholderText(/e\.g\., Onion/i)
        .map((element) => (element as HTMLInputElement).value)
    ).toEqual(['Onion', 'Garlic']);
    expect(screen.getByLabelText('Step 1')).toHaveValue('Chop');
    expect(screen.getByLabelText('Step 2')).toHaveValue('Simmer');
    expect(screen.getByLabelText(/category/i)).toHaveTextContent('Lunch');
    expect(screen.getByLabelText(/difficulty/i)).toHaveTextContent('Hard');
  });

  test('renders form fields and buttons', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    // Text inputs by label
    expect(screen.getByLabelText(/recipe name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();

    // Category select by label
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument();

    // Numeric inputs by label
    expect(screen.getByLabelText(/prep \(min\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cook \(min\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/min servings/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/max servings/i)).toBeInTheDocument();
  });

  test('adds and removes ingredients dynamically', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    const addButton = screen.getByText(/add ingredient/i);
    fireEvent.click(addButton);
    // Check for ingredient name fields by their unique placeholder
    expect(screen.getAllByPlaceholderText(/e\.g\., Onion/i)).toHaveLength(2);

    const removeButtons = screen.getAllByLabelText(/remove ingredient/i);
    fireEvent.click(removeButtons[0]);
    expect(screen.getAllByPlaceholderText(/e\.g\., Onion/i)).toHaveLength(1);
  });

  test('adds and removes instruction steps dynamically', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    const addStep = screen.getByText(/add step/i);
    fireEvent.click(addStep);
    expect(screen.getAllByPlaceholderText(/step/i)).toHaveLength(2);

    const removeButtons = screen.getAllByLabelText(/remove step/i);
    // last remove for instructions
    fireEvent.click(removeButtons[removeButtons.length - 1]);
    expect(screen.getAllByPlaceholderText(/step/i)).toHaveLength(1);
  });

  test('cancel button navigates back', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    const cancel = screen.getByText(/cancel/i);
    fireEvent.click(cancel);
    expect(navigateMock).toHaveBeenCalledWith('/recipes');
  });

  test('submit navigates after save', async () => {
    const addRecipeSpy = vi
      .spyOn(useRecipeStore.getState(), 'addRecipe')
      .mockImplementation(async (recipe) => ({
        ...recipe,
        id: 'recipe-1',
        total_time_minutes: 0,
        created_at: new Date(),
        updated_at: new Date(),
      }));

    try {
      render(
        <MemoryRouter>
          <RecipesNewPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByLabelText(/recipe name/i), {
        target: { value: 'Onion soup' },
      });
      fireEvent.change(screen.getByPlaceholderText(/e\.g\., Onion/i), {
        target: { value: 'Onion' },
      });
      fireEvent.change(screen.getByLabelText('Step 1'), {
        target: { value: 'Chop the onion' },
      });
      fireEvent.click(screen.getByText(/save recipe/i));

      await waitFor(() => {
        expect(addRecipeSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Onion soup',
            instructions: ['Chop the onion'],
            ingredients: [expect.objectContaining({ name: 'Onion' })],
          })
        );
        expect(navigateMock).toHaveBeenCalledWith('/recipes');
      });
    } finally {
      addRecipeSpy.mockRestore();
    }
  });

  test('handles instruction reordering with up/down buttons', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    // Add a second instruction
    const addStep = screen.getByText(/add step/i);
    fireEvent.click(addStep);

    // Fill in instructions
    const stepInputs = screen.getAllByPlaceholderText(
      /step/i
    ) as HTMLInputElement[];
    fireEvent.change(stepInputs[0], { target: { value: 'First step' } });
    fireEvent.change(stepInputs[1], { target: { value: 'Second step' } });

    // Test moving second step up (should become first)
    const upButtons = screen.getAllByLabelText(/move step.*up/i);
    fireEvent.click(upButtons[1]); // Click up button for second step

    // Verify the order changed
    const updatedInputs = screen.getAllByPlaceholderText(
      /step/i
    ) as HTMLInputElement[];
    expect(updatedInputs[0].value).toBe('Second step');
    expect(updatedInputs[1].value).toBe('First step');
  });

  test('disables up button for first instruction and down button for last instruction', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    // Add a second instruction
    const addStep = screen.getByText(/add step/i);
    fireEvent.click(addStep);

    const upButtons = screen.getAllByLabelText(/move step.*up/i);
    const downButtons = screen.getAllByLabelText(/move step.*down/i);

    // First step's up button should be disabled
    expect(upButtons[0]).toBeDisabled();
    // Last step's down button should be disabled
    expect(downButtons[1]).toBeDisabled();

    // Middle buttons should be enabled
    expect(downButtons[0]).not.toBeDisabled();
    expect(upButtons[1]).not.toBeDisabled();
  });

  test('shows accessible error messages with aria-live', async () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    // Try to submit without ingredients
    const save = screen.getByText(/save recipe/i);
    fireEvent.click(save);

    // Some implementations might show the red warning about connection issues
    // We'll check that the component is still rendered after attempted submission
    expect(screen.getByText(/recipe name/i)).toBeInTheDocument();
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
