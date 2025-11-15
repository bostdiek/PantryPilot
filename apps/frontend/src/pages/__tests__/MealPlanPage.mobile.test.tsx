import { render, screen, waitFor } from '@testing-library/react';
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

// Mock dnd-kit components for easier testing
vi.mock('@dnd-kit/core', async (orig) => {
  const actual = await (orig as any)();
  return {
    ...actual,
    DndContext: ({ children }: any) => (
      <div data-testid="dnd-context">{children}</div>
    ),
    DragOverlay: ({ children }: any) => (
      <div data-testid="drag-overlay">{children}</div>
    ),
    useDraggable: () => ({
      attributes: {},
      listeners: {},
      setNodeRef: vi.fn(),
    }),
    useDroppable: () => ({
      setNodeRef: vi.fn(),
      isOver: false,
    }),
    useSensor: vi.fn(),
    useSensors: () => [],
  };
});

vi.mock('@dnd-kit/sortable', async (orig) => {
  const actual = await (orig as any)();
  return {
    ...actual,
    SortableContext: ({ children }: any) => (
      <div data-testid="sortable-context">{children}</div>
    ),
    useSortable: () => ({
      attributes: {},
      listeners: {},
      setNodeRef: vi.fn(),
      transform: null,
      transition: null,
      isDragging: false,
    }),
  };
});

// Mock icons
vi.mock('../../components/ui/icons/check.svg?react', () => ({
  default: () => <span data-testid="icon-check" />,
}));
vi.mock('../../components/ui/icons/drag-handle.svg?react', () => ({
  default: () => <span data-testid="icon-drag" />,
}));
vi.mock('../../components/ui/icons/x.svg?react', () => ({
  default: () => <span data-testid="icon-x" />,
}));
vi.mock('../../components/ui/icons/chevron-up-down.svg?react', () => ({
  default: () => <span data-testid="icon-chevron" />,
}));

// Mock window.matchMedia for mobile testing
const mockMatchMedia = vi.fn();
beforeEach(() => {
  // Mock mobile viewport (375px width)
  mockMatchMedia.mockImplementation((query) => ({
    matches: query === '(max-width: 768px)', // Simulate mobile
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

describe('MealPlanPage - Mobile Recipe Title Visibility', () => {
  beforeEach(() => {
    // Reset stores
    const initialMealPlanState = useMealPlanStore.getState();
    const initialRecipeState = useRecipeStore.getState();

    useMealPlanStore.setState({
      ...initialMealPlanState,
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
                recipeId: 'r1',
              },
              {
                id: 'm2',
                plannedForDate: '2025-01-13',
                mealType: 'breakfast',
                isLeftover: false,
                isEatingOut: false,
                orderIndex: 1,
                wasCooked: false,
                recipeId: 'r2',
              },
            ],
          },
          {
            dayOfWeek: 'Tuesday',
            date: '2025-01-14',
            entries: [
              {
                id: 'm3',
                plannedForDate: '2025-01-14',
                mealType: 'lunch',
                isLeftover: false,
                isEatingOut: false,
                orderIndex: 0,
                wasCooked: false,
                recipeId: 'r3',
              },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    } as any);

    useRecipeStore.setState({
      ...initialRecipeState,
      recipes: [
        {
          id: 'r1',
          title:
            'This is an extremely long recipe title that should not be truncated and should be fully visible to users in the mobile meal planning interface so they can identify their planned meals',
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
        },
        {
          id: 'r2',
          title: 'Mac and Cheese with Extra Special Ingredients',
          ingredients: [
            {
              id: 'ing-2',
              name: 'Cheese',
              quantity_value: 100,
              quantity_unit: 'g',
            },
          ],
          total_time_minutes: 25,
          difficulty: 'easy',
        },
        {
          id: 'r3',
          title: 'Simple Omelette Recipe with Fresh Herbs and Vegetables',
          ingredients: [
            {
              id: 'ing-3',
              name: 'Eggs',
              quantity_value: 3,
              quantity_unit: 'pieces',
            },
          ],
          total_time_minutes: 15,
          difficulty: 'easy',
        },
      ] as any,
    } as any);
  });

  it('displays full recipe titles without truncation in mobile meal plan', async () => {
    render(<MealPlanPage />);

    await waitFor(() => {
      expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
    });

    // Check that long recipe titles are fully visible
    const longRecipeTitle = screen.getByText(
      /This is an extremely long recipe title/
    );
    expect(longRecipeTitle).toBeInTheDocument();

    // Verify the full text is visible, not truncated
    expect(longRecipeTitle).toHaveTextContent(
      'This is an extremely long recipe title that should not be truncated and should be fully visible to users in the mobile meal planning interface so they can identify their planned meals'
    );

    // Check other recipe titles are also fully visible
    expect(
      screen.getByText('Mac and Cheese with Extra Special Ingredients')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Simple Omelette Recipe with Fresh Herbs and Vegetables')
    ).toBeInTheDocument();
  });

  it('does not have line-clamp classes on recipe titles in meal entries', async () => {
    render(<MealPlanPage />);

    await waitFor(() => {
      expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
    });

    // Find recipe title elements
    const recipeButtons = screen.getAllByRole('button');
    const recipeButton = recipeButtons.find((button) =>
      button.textContent?.includes('This is an extremely long recipe title')
    );

    expect(recipeButton).toBeInTheDocument();

    // Check that the recipe title span doesn't have truncating classes
    const titleSpan = recipeButton?.querySelector('span');
    expect(titleSpan).not.toHaveClass('line-clamp-1');
    expect(titleSpan).not.toHaveClass('line-clamp-2');
    expect(titleSpan).not.toHaveClass('truncate');

    // Should have line-clamp-3 for proper wrapping with layout stability
    expect(titleSpan).toHaveClass('line-clamp-3');
  });

  it('allows interaction with recipe entries despite long titles', async () => {
    const user = userEvent.setup();
    render(<MealPlanPage />);

    await waitFor(() => {
      expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
    });

    // Find and click a recipe to test interactivity
    const recipeButton = screen.getByRole('button', {
      name: /View.*This is an extremely long recipe title.*recipe preview/i,
    });

    expect(recipeButton).toBeInTheDocument();
    await user.click(recipeButton);

    // Should trigger recipe preview modal (not navigation)
    await waitFor(() => {
      expect(screen.getAllByText('Ingredients')).toHaveLength(2); // Desktop + mobile
      expect(screen.getAllByText('View Full Recipe')).toHaveLength(2);
      expect(screen.getAllByText('Remove from Day')).toHaveLength(2);
    });
  });

  it('maintains proper layout with long recipe titles on mobile', async () => {
    const { container } = render(<MealPlanPage />);

    await waitFor(() => {
      expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
    });

    // Check that the meal plan container doesn't overflow
    const mealPlanContainer = container.querySelector(
      '[data-testid="dnd-context"]'
    );
    expect(mealPlanContainer).toBeInTheDocument();

    // Verify that long titles wrap properly and don't break layout
    const longTitleElement = screen.getByText(
      /This is an extremely long recipe title/
    );
    expect(longTitleElement).toBeInTheDocument();

    // The element should have line-clamp-3 class for proper text wrapping with layout stability
    expect(longTitleElement.className).toContain('line-clamp-3');
  });

  it('shows recipe metadata alongside full titles', async () => {
    render(<MealPlanPage />);

    await waitFor(() => {
      expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
    });

    // Check that recipe metadata (time, difficulty) is still visible
    expect(screen.getByText('30 min • easy')).toBeInTheDocument();
    expect(screen.getByText('25 min • easy')).toBeInTheDocument();
    expect(screen.getByText('15 min • easy')).toBeInTheDocument();

    // And that it's displayed alongside the full recipe titles
    const longRecipeContainer = screen
      .getByText(/This is an extremely long recipe title/)
      .closest('li');
    expect(longRecipeContainer).toBeInTheDocument();
    expect(longRecipeContainer).toHaveTextContent('30 min • easy');
  });
});
