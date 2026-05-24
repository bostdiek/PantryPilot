import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getMealProposalInstanceId,
  getMealProposalStatus,
  invalidateMealProposalStatus,
  markMealProposalAddedToPlan,
  markMealProposalRejected,
  markMealProposalSavedToBook,
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
  });
});
