import { describe, expect, it } from 'vitest';
import {
  addDaysToDateString,
  getLocalStartOfSundayWeek,
  toLocalYyyyMmDd,
} from '../dateUtils';

describe('dateUtils', () => {
  describe('toLocalYyyyMmDd', () => {
    it('should format date to YYYY-MM-DD in local timezone', () => {
      const date = new Date(2024, 0, 15); // January 15, 2024 (month is 0-indexed)
      const result = toLocalYyyyMmDd(date);
      expect(result).toBe('2024-01-15');
    });

    it('should pad month and day with zeros', () => {
      const date = new Date(2024, 0, 5); // January 5, 2024
      const result = toLocalYyyyMmDd(date);
      expect(result).toBe('2024-01-05');
    });

    it('should handle end of month correctly', () => {
      const date = new Date(2024, 0, 31); // January 31, 2024
      const result = toLocalYyyyMmDd(date);
      expect(result).toBe('2024-01-31');
    });
  });

  describe('getLocalStartOfSundayWeek', () => {
    it('should return Sunday for a Monday', () => {
      const monday = new Date(2024, 0, 15); // January 15, 2024 (Monday)
      const result = getLocalStartOfSundayWeek(monday);
      expect(result.getDay()).toBe(0); // Sunday
      expect(toLocalYyyyMmDd(result)).toBe('2024-01-14');
    });

    it('should return the same date if it is already Sunday', () => {
      const sunday = new Date(2024, 0, 14); // January 14, 2024 (Sunday)
      const result = getLocalStartOfSundayWeek(sunday);
      expect(result.getDay()).toBe(0); // Sunday
      expect(toLocalYyyyMmDd(result)).toBe('2024-01-14');
    });

    it('should return Sunday for a Saturday', () => {
      const saturday = new Date(2024, 0, 20); // January 20, 2024 (Saturday)
      const result = getLocalStartOfSundayWeek(saturday);
      expect(result.getDay()).toBe(0); // Sunday
      expect(toLocalYyyyMmDd(result)).toBe('2024-01-14');
    });

    it('should handle cross-month boundaries', () => {
      const date = new Date(2024, 1, 1); // February 1, 2024 (Thursday)
      const result = getLocalStartOfSundayWeek(date);
      expect(result.getDay()).toBe(0); // Sunday
      expect(toLocalYyyyMmDd(result)).toBe('2024-01-28'); // Previous month
    });
  });

  describe('addDaysToDateString', () => {
    it('should add positive days', () => {
      const result = addDaysToDateString('2024-01-15', 7);
      expect(result).toBe('2024-01-22');
    });

    it('should subtract days with negative input', () => {
      const result = addDaysToDateString('2024-01-15', -7);
      expect(result).toBe('2024-01-08');
    });

    it('should handle month boundaries', () => {
      const result = addDaysToDateString('2024-01-31', 1);
      expect(result).toBe('2024-02-01');
    });

    it('should handle year boundaries', () => {
      const result = addDaysToDateString('2023-12-31', 1);
      expect(result).toBe('2024-01-01');
    });

    it('should handle leap years', () => {
      const result = addDaysToDateString('2024-02-28', 1);
      expect(result).toBe('2024-02-29'); // 2024 is a leap year
    });

    it('should handle non-leap years', () => {
      const result = addDaysToDateString('2023-02-28', 1);
      expect(result).toBe('2023-03-01'); // 2023 is not a leap year
    });
  });
});
