import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getMealProposalStatus,
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
        savedToBook: false,
        addedToPlan: false,
        rejected: false,
      });
    });

    it('returns correct status after marking savedToBook', () => {
      markMealProposalSavedToBook('test-proposal');
      const status = getMealProposalStatus('test-proposal');
      expect(status.savedToBook).toBe(true);
      expect(status.addedToPlan).toBe(false);
      expect(status.rejected).toBe(false);
    });

    it('returns correct status after marking addedToPlan', () => {
      markMealProposalAddedToPlan('test-proposal');
      const status = getMealProposalStatus('test-proposal');
      expect(status.savedToBook).toBe(false);
      expect(status.addedToPlan).toBe(true);
      expect(status.rejected).toBe(false);
    });

    it('returns correct status after marking rejected', () => {
      markMealProposalRejected('test-proposal');
      const status = getMealProposalStatus('test-proposal');
      expect(status.savedToBook).toBe(false);
      expect(status.addedToPlan).toBe(false);
      expect(status.rejected).toBe(true);
    });

    it('handles multiple flags being set', () => {
      markMealProposalSavedToBook('test-proposal');
      markMealProposalAddedToPlan('test-proposal');
      const status = getMealProposalStatus('test-proposal');
      expect(status.savedToBook).toBe(true);
      expect(status.addedToPlan).toBe(true);
      expect(status.rejected).toBe(false);
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
    it('returns false when localStorage throws on read', () => {
      const getItemSpy = vi
        .spyOn(Storage.prototype, 'getItem')
        .mockImplementation(() => {
          throw new Error('Storage unavailable');
        });

      const status = getMealProposalStatus('test-proposal');
      expect(status).toEqual({
        savedToBook: false,
        addedToPlan: false,
        rejected: false,
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
