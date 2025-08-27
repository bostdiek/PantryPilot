import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as client from '../client';
import {
  createMealEntry,
  deleteMealEntry,
  getWeeklyMealPlan,
  markMealCooked,
  replaceWeeklyMealPlan,
  updateMealEntry,
} from '../endpoints/mealPlans';

const mockRequest = vi.spyOn(client.apiClient, 'request');

beforeEach(() => {
  mockRequest.mockReset();
});

describe('mealPlans API adapters', () => {
  it('getWeeklyMealPlan adapts snake->camel', async () => {
    mockRequest.mockResolvedValueOnce({
      week_start_date: '2025-01-12',
      days: [
        {
          day_of_week: 'Sunday',
          date: '2025-01-12',
          entries: [
            {
              id: '1',
              planned_for_date: '2025-01-12',
              meal_type: 'dinner',
              recipe_id: null,
              is_leftover: false,
              is_eating_out: false,
              notes: null,
              order_index: 0,
              was_cooked: false,
              cooked_at: null,
            },
          ],
        },
      ],
    });

    const res = await getWeeklyMealPlan('2025-01-12');
    expect(res.weekStartDate).toBe('2025-01-12');
    expect(res.days[0].entries[0]).toMatchObject({
      id: '1',
      plannedForDate: '2025-01-12',
      orderIndex: 0,
      wasCooked: false,
    });
  });

  it('replaceWeeklyMealPlan adapts camel->snake payload', async () => {
    mockRequest.mockResolvedValueOnce({
      week_start_date: '2025-01-12',
      days: [],
    });

    const res = await replaceWeeklyMealPlan(
      [
        {
          plannedForDate: '2025-01-12',
          recipeId: 'abc',
          isLeftover: false,
          isEatingOut: false,
          notes: 'note',
          orderIndex: 1,
        },
      ],
      '2025-01-12'
    );
    expect(res.weekStartDate).toBe('2025-01-12');
    const call = mockRequest.mock.calls[0];
    expect(call[0]).toContain('/api/v1/mealplans/weekly?start=2025-01-12');
    expect(JSON.parse((call[1] as any).body)[0]).toMatchObject({
      planned_for_date: '2025-01-12',
      recipe_id: 'abc',
      order_index: 1,
    });
  });

  it('create/update/delete/markCooked adapt correctly', async () => {
    mockRequest
      .mockResolvedValueOnce({
        id: 'm1',
        planned_for_date: '2025-01-13',
        meal_type: 'dinner',
        recipe_id: 'r1',
        is_leftover: false,
        is_eating_out: false,
        notes: null,
        order_index: 0,
        was_cooked: false,
        cooked_at: null,
      })
      .mockResolvedValueOnce({
        id: 'm1',
        planned_for_date: '2025-01-14',
        meal_type: 'dinner',
        recipe_id: 'r1',
        is_leftover: false,
        is_eating_out: false,
        notes: null,
        order_index: 2,
        was_cooked: false,
        cooked_at: null,
      })
      .mockResolvedValueOnce({ success: true })
      .mockResolvedValueOnce({
        id: 'm1',
        planned_for_date: '2025-01-14',
        meal_type: 'dinner',
        recipe_id: 'r1',
        is_leftover: false,
        is_eating_out: false,
        notes: null,
        order_index: 2,
        was_cooked: true,
        cooked_at: '2025-01-14T18:00:00Z',
      });

    const created = await createMealEntry({
      plannedForDate: '2025-01-13',
      recipeId: 'r1',
      orderIndex: 0,
    });
    expect(created.plannedForDate).toBe('2025-01-13');

    const updated = await updateMealEntry('m1', {
      plannedForDate: '2025-01-14',
      orderIndex: 2,
    });
    expect(updated.orderIndex).toBe(2);

    const del = await deleteMealEntry('m1');
    expect(del).toEqual({ success: true });

    const cooked = await markMealCooked('m1', '2025-01-14T18:00:00Z');
    expect(cooked.wasCooked).toBe(true);
    expect(cooked.cookedAt).toBe('2025-01-14T18:00:00Z');
  });
});
