import { describe, expect, it } from 'vitest';
import { coerceToString, getRegisterFallbackMessage } from '../errorMessages';

describe('coerceToString', () => {
  it('returns string input unchanged', () => {
    expect(coerceToString('hello')).toBe('hello');
  });

  it('returns empty string for null/undefined', () => {
    expect(coerceToString(null)).toBe('');
    expect(coerceToString(undefined)).toBe('');
  });

  it('serializes non-empty objects', () => {
    const obj = { a: 1, b: 'x' };
    const s = coerceToString(obj);
    expect(typeof s).toBe('string');
    expect(s).toContain('"a":1');
    expect(s).toContain('"b":"x"');
  });

  it('returns empty string for empty object', () => {
    expect(coerceToString({})).toBe('');
  });

  it('falls back to String() for non-serializable objects', () => {
    // Create an object with circular reference
    const a: any = { x: 1 };
    a.self = a;
    const s = coerceToString(a);
    expect(typeof s).toBe('string');
    expect(s.length).toBeGreaterThan(0);
  });
});

describe('getRegisterFallbackMessage', () => {
  it('returns validation error for 422 with validation wording', () => {
    const msg = 'Validation failed: field email is required';
    expect(getRegisterFallbackMessage(msg, 422)).toBe(
      'Please check your input and try again.'
    );
  });

  it('returns registration-specific fallback for 422 without validation wording', () => {
    const msg = 'username conflict detected';
    expect(getRegisterFallbackMessage(msg, 422)).toBe(
      'Invalid registration data. Please check your inputs.'
    );
  });

  it('returns combined guidance when username and email both mentioned', () => {
    const msg = 'username and email already exist';
    expect(getRegisterFallbackMessage(msg, 400)).toBe(
      'An account with this email or username already exists. Please try logging in instead.'
    );
  });

  it('returns undefined when no special fallback applies', () => {
    expect(getRegisterFallbackMessage('some minor error', 400)).toBeUndefined();
  });
});
