import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMealPlanStore } from '../../stores/useMealPlanStore';
import { useRecipeStore } from '../../stores/useRecipeStore';
import MealPlanPage from '../MealPlanPage';

// Mock router navigation
const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual('react-router-dom')),
  useNavigate: () => navigateMock,
}));

// Minimal mock for dnd-kit portal usage in tests (no real DnD simulation here)
vi.mock('@dnd-kit/core', async (orig) => {
  const actual = await (orig as any)();
  return {
    ...actual,
    DndContext: ({ children }: any) => <div>{children}</div>,
    DragOverlay: ({ children }: any) => (
      <div data-testid="overlay">{children}</div>
    ),
    useDraggable: () => ({
      attributes: {},
      listeners: {},
      setNodeRef: vi.fn(),
    }),
    useDroppable: () => ({ setNodeRef: vi.fn(), isOver: false }),
  };
});

// Mock icons imported by the page
vi.mock('../../components/ui/icons/check.svg?react', () => ({
  default: () => <span data-testid="icon-check" />,
}));
vi.mock('../../components/ui/icons/x.svg?react', () => ({
  default: () => <span data-testid="icon-x" />,
}));
vi.mock('../../components/ui/icons/drag-handle.svg?react', () => ({
  default: () => <span data-testid="icon-drag" />,
}));
// Mock SVG icon components used by Select to avoid jsdom parsing inline SVG data URLs
vi.mock('../../components/ui/icons/check.svg?react', () => ({
  default: () => <span data-testid="icon-check" />,
}));
vi.mock('../../components/ui/icons/chevron-up-down.svg?react', () => ({
  default: () => <span data-testid="icon-chevron" />,
}));

// Mock window.matchMedia for media query hooks
const mockMatchMedia = vi.fn();
beforeEach(() => {
  mockMatchMedia.mockImplementation((query) => ({
    matches: false, // Default to desktop/non-mobile
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: mockMatchMedia,
  });
});

// NOTE: matchMedia is mocked in the beforeEach above; do not redefine it here.

beforeEach(() => {
  // Get the initial state with all methods
  const initialState = useMealPlanStore.getState();

  // Seed store state with a simple week and one entry
  useMealPlanStore.setState({
    ...initialState,
    currentWeek: {
      weekStartDate: '2025-01-12',
      days: [
        {
          dayOfWeek: 'Monday',
          date: '2025-01-13',
          entries: [
            {
              id: 'm1',
              plannedForDate: '2025-01-13',
              mealType: 'dinner',
              isLeftover: false,
              isEatingOut: false,
              orderIndex: 0,
              wasCooked: false,
            },
          ],
        },
      ],
    },
    isLoading: false,
    error: null,
  } as any);

  useRecipeStore.setState({
    recipes: [
      {
        id: 'r1',
        title: 'Spaghetti',
        ingredients: [
          {
            id: 'ing-1',
            name: 'Pasta',
            quantity_value: 200,
            quantity_unit: 'g',
          },
        ],
        total_time_minutes: 30,
        difficulty: 'easy',
      } as any,
    ],
  } as any);
});

describe('MealPlanPage', () => {
  it('renders a planned entry and marks it cooked', async () => {
    const user = userEvent.setup();
    // Override markCooked with a spy that also mutates state to reflect cooked status
    const markSpy = vi.fn(async (id: string) => {
      const state = useMealPlanStore.getState();
      const week = state.currentWeek;
      if (!week) return;
      for (const d of week.days) {
        const idx = d.entries.findIndex((e) => e.id === id);
        if (idx !== -1) {
          d.entries[idx] = {
            ...d.entries[idx],
            wasCooked: true,
            cookedAt: new Date().toISOString(),
          } as any;
          break;
        }
      }
      useMealPlanStore.setState({ currentWeek: { ...week } } as any);
    });
    useMealPlanStore.setState((s) => ({ ...(s as any), markCooked: markSpy }));

    render(<MealPlanPage />);

    // Find the entry item and then the scoped Cooked button within it
    const entryItem = screen.getByText('Planned item').closest('li')!;
    const cookedBtn = within(entryItem).getByLabelText(
      /Mark Planned item as cooked/i
    );
    await user.click(cookedBtn);

    await waitFor(() => expect(markSpy).toHaveBeenCalledTimes(1));
    expect(markSpy.mock.calls[0][0]).toBe('m1');

    // no restore needed; state reset by test beforeEach
  });

  it('removes an entry when clicking Remove', async () => {
    const user = userEvent.setup();
    const removeSpy = vi
      .spyOn(useMealPlanStore.getState(), 'removeEntry')
      .mockResolvedValue(undefined);

    render(<MealPlanPage />);

    const entryItem = screen.getByText('Planned item').closest('li')!;
    const removeBtn = within(entryItem).getByRole('button', {
      name: /Remove/i,
    });
    await user.click(removeBtn);

    expect(removeSpy).toHaveBeenCalledTimes(1);
    expect(removeSpy.mock.calls[0][0]).toBe('m1');
  });

  it('navigates to previous week via controls', async () => {
    const user = userEvent.setup();
    const loadSpy = vi
      .spyOn(useMealPlanStore.getState(), 'loadWeek')
      .mockResolvedValue(undefined);

    render(<MealPlanPage />);

    const prevBtn = screen.getByRole('button', { name: /Previous week/i });
    await user.click(prevBtn);

    // Given weekStartDate is 2025-01-12 in beforeEach, previous week is 2025-01-05
    expect(loadSpy).toHaveBeenCalledWith('2025-01-05');
  });

  it('opens recipe preview when clicking on recipe name', async () => {
    const user = userEvent.setup();

    // Setup a recipe entry instead of the default planned item
    useMealPlanStore.setState({
      currentWeek: {
        weekStartDate: '2025-01-12',
        days: [
          {
            dayOfWeek: 'Sunday',
            date: '2025-01-12',
            entries: [
              {
                id: 'm1',
                plannedForDate: '2025-01-12',
                mealType: 'dinner',
                recipeId: 'r1', // This connects to the recipe in our mock data
                isLeftover: false,
                isEatingOut: false,
                orderIndex: 0,
                wasCooked: false,
              },
            ],
          },
        ],
      },
    } as any);

    render(<MealPlanPage />);

    // Find the recipe title (should be clickable and blue)
    const recipeButton = screen.getByLabelText('View Spaghetti recipe preview');
    expect(recipeButton).toBeInTheDocument();

    // The blue color is on the child span, not the button itself
    const recipeText = within(recipeButton).getByText('Spaghetti');
    expect(recipeText).toHaveClass('text-blue-600');

    // Click the recipe name
    await user.click(recipeButton);

    // Should open the quick preview modal with recipe details
    expect(screen.getAllByText('Ingredients')).toHaveLength(2); // Desktop + mobile
    expect(screen.getAllByText('View Full Recipe')).toHaveLength(2);
    expect(screen.getAllByText('Remove from Day')).toHaveLength(2);
  });

  it('navigates to recipe detail when clicking View Full Recipe', async () => {
    const user = userEvent.setup();

    // Setup a recipe entry
    useMealPlanStore.setState({
      currentWeek: {
        weekStartDate: '2025-01-12',
        days: [
          {
            dayOfWeek: 'Sunday',
            date: '2025-01-12',
            entries: [
              {
                id: 'm1',
                plannedForDate: '2025-01-12',
                mealType: 'dinner',
                recipeId: 'r1',
                isLeftover: false,
                isEatingOut: false,
                orderIndex: 0,
                wasCooked: false,
              },
            ],
          },
        ],
      },
    } as any);

    render(<MealPlanPage />);

    // Open the quick preview
    const recipeButton = screen.getByLabelText('View Spaghetti recipe preview');
    await user.click(recipeButton);

    // Click "View Full Recipe" button (desktop version)
    const viewFullButtons = screen.getAllByText('View Full Recipe');
    await user.click(viewFullButtons[0]);

    // Should navigate to recipe detail page with context params
    expect(navigateMock).toHaveBeenCalledWith(
      '/recipes/r1?from=mealplan&d=2025-01-12'
    );
  });

  it('removes recipe from day when clicking Remove from Day', async () => {
    const user = userEvent.setup();

    const removeSpy = vi
      .spyOn(useMealPlanStore.getState(), 'removeEntry')
      .mockResolvedValue(undefined);

    // Setup a recipe entry
    useMealPlanStore.setState({
      currentWeek: {
        weekStartDate: '2025-01-12',
        days: [
          {
            dayOfWeek: 'Sunday',
            date: '2025-01-12',
            entries: [
              {
                id: 'm1',
                plannedForDate: '2025-01-12',
                mealType: 'dinner',
                recipeId: 'r1',
                isLeftover: false,
                isEatingOut: false,
                orderIndex: 0,
                wasCooked: false,
              },
            ],
          },
        ],
      },
    } as any);

    render(<MealPlanPage />);

    // Open the quick preview
    const recipeButton = screen.getByLabelText('View Spaghetti recipe preview');
    await user.click(recipeButton);

    // Click "Remove from Day" button (desktop version)
    const removeButtons = screen.getAllByText('Remove from Day');
    await user.click(removeButtons[0]);

    // Should call removeEntry with the correct entry ID
    expect(removeSpy).toHaveBeenCalledWith('m1');

    // Wait for async operation to complete and modal to close
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Modal should be closed after successful removal
    expect(screen.queryByText('Ingredients')).not.toBeInTheDocument();
  });
});
