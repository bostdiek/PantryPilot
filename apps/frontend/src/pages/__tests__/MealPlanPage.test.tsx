import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMealPlanStore } from '../../stores/useMealPlanStore';
import { useRecipeStore } from '../../stores/useRecipeStore';
import MealPlanPage from '../MealPlanPage';

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

// Mock SVG icon components used by Select to avoid jsdom parsing inline SVG data URLs
vi.mock('../../components/ui/icons/check.svg?react', () => ({
  default: () => <span data-testid="icon-check" />,
}));
vi.mock('../../components/ui/icons/chevron-up-down.svg?react', () => ({
  default: () => <span data-testid="icon-chevron" />,
}));

beforeEach(() => {
  // Seed store state with a simple week and one entry
  useMealPlanStore.setState({
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
        total_time_minutes: 30,
        difficulty: 'easy',
      } as any,
    ],
  } as any);
});

describe('MealPlanPage', () => {
  it('renders a planned entry and marks it cooked', async () => {
    const user = userEvent.setup();

    // Spy on store markCooked to ensure it is invoked by the button
    const markSpy = vi
      .spyOn(useMealPlanStore.getState(), 'markCooked')
      .mockResolvedValue();

    render(<MealPlanPage />);

    // Find the entry item and then the scoped Cooked button within it
    const entryItem = screen.getByText('Planned item').closest('li')!;
    const cookedBtn = within(entryItem).getByRole('button', {
      name: /Cooked/i,
    });
    await user.click(cookedBtn);

    expect(markSpy).toHaveBeenCalledTimes(1);
    expect(markSpy.mock.calls[0][0]).toBe('m1');
  });
});
