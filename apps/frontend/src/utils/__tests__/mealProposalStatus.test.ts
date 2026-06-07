import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getMealProposalInstanceId,
  getMealProposalStatus,
  invalidateMealProposalStatus,
  markMealProposalAddedToPlan,
  markMealProposalRejected,
  markMealProposalRetryableAddFailure,
  markMealProposalSavedToBook,
  resetMealProposalStatus,
  setMealProposalStatus,
} from '../mealProposalStatus';

describe('mealProposalStatus', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('getMealProposalStatus', () => {
    it('returns all false for unknown proposal', () => {
      const status = getMealProposalStatus('unknown-proposal');
      expect(status).toEqual({
        version: 1,
        phase: 'pending',
        updatedAt: undefined,
        proposalInstanceId: undefined,
        recipeId: undefined,
        returnContext: undefined,
        lastError: undefined,
        savedToBook: false,
        addedToPlan: false,
        rejected: false,
        canRetryAdd: false,
      });
    });

    it('returns correct status after marking savedToBook', () => {
      markMealProposalSavedToBook('test-proposal', {
        proposalInstanceId: 'proposal-1',
      });
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('recipe_saved');
      expect(status.proposalInstanceId).toBe('proposal-1');
      expect(status.savedToBook).toBe(true);
      expect(status.addedToPlan).toBe(false);
      expect(status.rejected).toBe(false);
      expect(status.canRetryAdd).toBe(true);
    });

    it('returns correct status after marking addedToPlan', () => {
      markMealProposalAddedToPlan('test-proposal', {
        proposalInstanceId: 'proposal-2',
      });
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('added_to_plan');
      expect(status.proposalInstanceId).toBe('proposal-2');
      expect(status.savedToBook).toBe(false);
      expect(status.addedToPlan).toBe(true);
      expect(status.rejected).toBe(false);
      expect(status.canRetryAdd).toBe(false);
    });

    it('returns correct status after marking rejected', () => {
      markMealProposalRejected('test-proposal');
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('rejected');
      expect(status.savedToBook).toBe(false);
      expect(status.addedToPlan).toBe(false);
      expect(status.rejected).toBe(true);
      expect(status.canRetryAdd).toBe(false);
    });

    it('handles multiple flags being set', () => {
      markMealProposalSavedToBook('test-proposal');
      markMealProposalAddedToPlan('test-proposal');
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('added_to_plan');
      expect(status.savedToBook).toBe(false);
      expect(status.addedToPlan).toBe(true);
      expect(status.rejected).toBe(false);
      expect(status.canRetryAdd).toBe(false);
    });

    it('handles different proposals independently', () => {
      markMealProposalSavedToBook('proposal-1');
      markMealProposalAddedToPlan('proposal-2');
      markMealProposalRejected('proposal-3');

      expect(getMealProposalStatus('proposal-1').savedToBook).toBe(true);
      expect(getMealProposalStatus('proposal-1').addedToPlan).toBe(false);

      expect(getMealProposalStatus('proposal-2').addedToPlan).toBe(true);
      expect(getMealProposalStatus('proposal-2').savedToBook).toBe(false);

      expect(getMealProposalStatus('proposal-3').rejected).toBe(true);
      expect(getMealProposalStatus('proposal-3').savedToBook).toBe(false);
    });
  });

  describe('error handling', () => {
    it('extracts the proposal instance from the persisted proposal key', () => {
      expect(
        getMealProposalInstanceId('proposal-123|url:https://example.com')
      ).toBe('proposal-123');
    });

    it('clears stale persisted state when the proposal instance changes', () => {
      markMealProposalSavedToBook('test-proposal', {
        proposalInstanceId: 'proposal-1',
      });

      invalidateMealProposalStatus('test-proposal', 'proposal-2');

      expect(getMealProposalStatus('test-proposal').phase).toBe('pending');
    });

    it('returns false when localStorage throws on read', () => {
      const getItemSpy = vi
        .spyOn(Storage.prototype, 'getItem')
        .mockImplementation(() => {
          throw new Error('Storage unavailable');
        });

      const status = getMealProposalStatus('test-proposal');
      expect(status).toEqual({
        version: 1,
        phase: 'pending',
        updatedAt: undefined,
        proposalInstanceId: undefined,
        recipeId: undefined,
        returnContext: undefined,
        lastError: undefined,
        savedToBook: false,
        addedToPlan: false,
        rejected: false,
        canRetryAdd: false,
      });

      getItemSpy.mockRestore();
    });

    it('does not throw when localStorage throws on write', () => {
      const setItemSpy = vi
        .spyOn(Storage.prototype, 'setItem')
        .mockImplementation(() => {
          throw new Error('Storage unavailable');
        });

      // Should not throw
      expect(() => markMealProposalSavedToBook('test-proposal')).not.toThrow();
      expect(() => markMealProposalAddedToPlan('test-proposal')).not.toThrow();
      expect(() => markMealProposalRejected('test-proposal')).not.toThrow();

      setItemSpy.mockRestore();
    });

    it('does not throw when localStorage throws on remove', () => {
      markMealProposalSavedToBook('test-proposal');
      const removeItemSpy = vi
        .spyOn(Storage.prototype, 'removeItem')
        .mockImplementation(() => {
          throw new Error('Storage unavailable');
        });

      expect(() => resetMealProposalStatus('test-proposal')).not.toThrow();

      removeItemSpy.mockRestore();
    });
  });

  describe('retryable add failure', () => {
    it('marks proposal as retryable_add_failure', () => {
      markMealProposalRetryableAddFailure('test-proposal', {
        proposalInstanceId: 'proposal-1',
        recipeId: 'recipe-123',
        lastError: 'meal_entry_create_failed',
      });
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('retryable_add_failure');
      expect(status.proposalInstanceId).toBe('proposal-1');
      expect(status.recipeId).toBe('recipe-123');
      expect(status.lastError).toBe('meal_entry_create_failed');
      expect(status.savedToBook).toBe(true);
      expect(status.canRetryAdd).toBe(true);
      expect(status.addedToPlan).toBe(false);
    });

    it('transitions from retryable_add_failure to added_to_plan', () => {
      markMealProposalRetryableAddFailure('test-proposal', {
        proposalInstanceId: 'proposal-1',
        lastError: 'meal_entry_create_failed',
      });
      markMealProposalAddedToPlan('test-proposal', {
        proposalInstanceId: 'proposal-1',
      });
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('added_to_plan');
      expect(status.canRetryAdd).toBe(false);
      expect(status.lastError).toBeUndefined();
    });
  });

  describe('setMealProposalStatus', () => {
    it('merges update with existing status', () => {
      markMealProposalSavedToBook('test-proposal', {
        proposalInstanceId: 'proposal-1',
      });
      setMealProposalStatus('test-proposal', {
        phase: 'adding_to_plan',
        proposalInstanceId: 'proposal-1',
      });
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('adding_to_plan');
      expect(status.proposalInstanceId).toBe('proposal-1');
    });

    it('stores and retrieves returnContext', () => {
      markMealProposalSavedToBook('test-proposal', {
        proposalInstanceId: 'proposal-1',
        returnContext: {
          proposalKey: 'test-proposal',
          chatConversationId: 'chat-1',
          mealPlanDate: '2026-01-26',
          mealPlanDayLabel: 'Monday',
        },
      });
      const status = getMealProposalStatus('test-proposal');
      expect(status.returnContext).toEqual({
        proposalKey: 'test-proposal',
        chatConversationId: 'chat-1',
        mealPlanDate: '2026-01-26',
        mealPlanDayLabel: 'Monday',
      });
    });
  });

  describe('resetMealProposalStatus', () => {
    it('clears persisted status back to pending', () => {
      markMealProposalAddedToPlan('test-proposal', {
        proposalInstanceId: 'proposal-1',
      });
      resetMealProposalStatus('test-proposal');
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('pending');
      expect(status.addedToPlan).toBe(false);
    });
  });

  describe('invalidateMealProposalStatus', () => {
    it('does not clear status when instance matches', () => {
      markMealProposalSavedToBook('test-proposal', {
        proposalInstanceId: 'proposal-1',
      });
      invalidateMealProposalStatus('test-proposal', 'proposal-1');
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('recipe_saved');
    });

    it('does not clear status when no persisted state exists', () => {
      invalidateMealProposalStatus('test-proposal', 'proposal-1');
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('pending');
    });
  });

  describe('getMealProposalInstanceId', () => {
    it('returns full key when no pipe separator present', () => {
      expect(getMealProposalInstanceId('proposal-123')).toBe('proposal-123');
    });
  });

  describe('legacy migration', () => {
    it('migrates legacy savedToBook flag to recipe_saved phase', () => {
      localStorage.setItem(
        'pantrypilot_meal_proposal:test-proposal:savedToBook',
        '1'
      );
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('recipe_saved');
      expect(status.savedToBook).toBe(true);
      // Legacy key should be cleaned up
      expect(
        localStorage.getItem(
          'pantrypilot_meal_proposal:test-proposal:savedToBook'
        )
      ).toBeNull();
    });

    it('migrates legacy addedToPlan flag to added_to_plan phase', () => {
      localStorage.setItem(
        'pantrypilot_meal_proposal:test-proposal:addedToPlan',
        '1'
      );
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('added_to_plan');
      expect(status.addedToPlan).toBe(true);
    });

    it('migrates legacy rejected flag to rejected phase', () => {
      localStorage.setItem(
        'pantrypilot_meal_proposal:test-proposal:rejected',
        '1'
      );
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('rejected');
      expect(status.rejected).toBe(true);
    });

    it('resets corrupted persisted status', () => {
      localStorage.setItem(
        'pantrypilot_meal_proposal:test-proposal:status',
        JSON.stringify({ version: 1, phase: 'invalid_phase' })
      );
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('pending');
    });

    it('resets persisted status with wrong version', () => {
      localStorage.setItem(
        'pantrypilot_meal_proposal:test-proposal:status',
        JSON.stringify({ version: 99, phase: 'pending' })
      );
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('pending');
    });

    it('resets unparseable JSON in storage', () => {
      localStorage.setItem(
        'pantrypilot_meal_proposal:test-proposal:status',
        'not-json-at-all'
      );
      const status = getMealProposalStatus('test-proposal');
      expect(status.phase).toBe('pending');
    });
  });
});
