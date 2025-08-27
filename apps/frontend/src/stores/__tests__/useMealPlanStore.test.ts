import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../api/endpoints/mealPlans';
import { useMealPlanStore } from '../../stores/useMealPlanStore';

vi.mock('../../api/endpoints/mealPlans', async (orig) => {
  const actual = await (orig as any)();
  return {
    ...actual,
    getWeeklyMealPlan: vi.fn(),
    createMealEntry: vi.fn(),
    updateMealEntry: vi.fn(),
    deleteMealEntry: vi.fn(),
    markMealCooked: vi.fn(),
  } as typeof import('../../api/endpoints/mealPlans');
});

const mocked = api as unknown as {
  getWeeklyMealPlan: ReturnType<typeof vi.fn>;
  createMealEntry: ReturnType<typeof vi.fn>;
  updateMealEntry: ReturnType<typeof vi.fn>;
  deleteMealEntry: ReturnType<typeof vi.fn>;
  markMealCooked: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.clearAllMocks();
  // reset store state between tests
  const { setState } = useMealPlanStore;
  setState({ currentWeek: null, isLoading: false, error: null } as any);
});

describe('useMealPlanStore', () => {
  it('loads a week and sets state', async () => {
    mocked.getWeeklyMealPlan.mockResolvedValueOnce({
      weekStartDate: '2025-01-12',
      days: [
        { date: '2025-01-12', dayOfWeek: 'Sunday', entries: [] },
        { date: '2025-01-13', dayOfWeek: 'Monday', entries: [] },
      ],
    });

    await useMealPlanStore.getState().loadWeek('2025-01-12');
    const st = useMealPlanStore.getState();
    expect(st.currentWeek?.weekStartDate).toBe('2025-01-12');
    expect(st.isLoading).toBe(false);
    expect(st.error).toBeNull();
  });

  it('adds an entry to the correct day ordered by orderIndex', async () => {
    useMealPlanStore.setState({
      currentWeek: {
        weekStartDate: '2025-01-12',
        days: [{ date: '2025-01-13', dayOfWeek: 'Monday', entries: [] }],
      },
      isLoading: false,
      error: null,
    } as any);

    mocked.createMealEntry.mockResolvedValueOnce({
      id: 'm1',
      plannedForDate: '2025-01-13',
      mealType: 'dinner',
      isLeftover: false,
      isEatingOut: false,
      orderIndex: 1,
      wasCooked: false,
    });

    await useMealPlanStore.getState().addEntry({
      plannedForDate: '2025-01-13',
      orderIndex: 1,
    });

    const day = useMealPlanStore
      .getState()
      .currentWeek!.days.find((d) => d.date === '2025-01-13')!;
    expect(day.entries[0].id).toBe('m1');
    expect(day.entries[0].orderIndex).toBe(1);
  });

  it('updates an entry and moves days when plannedForDate changes', async () => {
    useMealPlanStore.setState({
      currentWeek: {
        weekStartDate: '2025-01-12',
        days: [
          {
            date: '2025-01-13',
            dayOfWeek: 'Monday',
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
          { date: '2025-01-14', dayOfWeek: 'Tuesday', entries: [] },
        ],
      },
      isLoading: false,
      error: null,
    } as any);

    mocked.updateMealEntry.mockResolvedValueOnce({
      id: 'm1',
      plannedForDate: '2025-01-14',
      mealType: 'dinner',
      isLeftover: false,
      isEatingOut: false,
      orderIndex: 1,
      wasCooked: false,
    });

    await useMealPlanStore.getState().updateEntry('m1', {
      plannedForDate: '2025-01-14',
      orderIndex: 1,
    });

    const st = useMealPlanStore.getState();
    const monday = st.currentWeek!.days.find((d) => d.date === '2025-01-13')!;
    const tuesday = st.currentWeek!.days.find((d) => d.date === '2025-01-14')!;
    expect(monday.entries.length).toBe(0);
    expect(tuesday.entries.map((e) => e.id)).toEqual(['m1']);
    expect(tuesday.entries[0].orderIndex).toBe(1);
  });

  it('marks cooked in place', async () => {
    useMealPlanStore.setState({
      currentWeek: {
        weekStartDate: '2025-01-12',
        days: [
          {
            date: '2025-01-13',
            dayOfWeek: 'Monday',
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

    mocked.markMealCooked.mockResolvedValueOnce({
      id: 'm1',
      plannedForDate: '2025-01-13',
      mealType: 'dinner',
      isLeftover: false,
      isEatingOut: false,
      orderIndex: 0,
      wasCooked: true,
      cookedAt: '2025-01-13T18:00:00Z',
    });

    await useMealPlanStore.getState().markCooked('m1', '2025-01-13T18:00:00Z');
    const entry = useMealPlanStore.getState().currentWeek!.days[0].entries[0];
    expect(entry.wasCooked).toBe(true);
    expect(entry.cookedAt).toBe('2025-01-13T18:00:00Z');
  });
});
