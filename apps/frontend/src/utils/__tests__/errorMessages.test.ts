import { describe, it, expect } from 'vitest';
import {
  getUserFriendlyErrorMessage,
  shouldLogoutOnError,
  getRetryBehavior,
} from '../errorMessages';

describe('getUserFriendlyErrorMessage', () => {
  it('handles string error messages', () => {
    const result = getUserFriendlyErrorMessage('Network error occurred');
    expect(result).toBe(
      'Unable to connect. Please check your internet connection and try again.'
    );
  });

  it('handles error objects with message field', () => {
    const error = {
      message: 'Username or email already exists',
      status: 409,
    };
    const result = getUserFriendlyErrorMessage(error);
    expect(result).toBe(
      'An account with this email or username already exists.'
    );
  });

  it('handles validation errors with context', () => {
    const error = {
      message: 'Validation failed',
      status: 422,
    };
    const result = getUserFriendlyErrorMessage(error, { action: 'register' });
    expect(result).toBe('Please check your input and try again.');
  });

  it('handles authentication errors', () => {
    const error = {
      message: 'Unauthorized',
      status: 401,
    };
    const result = getUserFriendlyErrorMessage(error);
    expect(result).toBe('Please log in to continue.');
  });

  it('prioritizes canonical error types over message patterns', () => {
    const error = {
      message: 'Some generic message',
      error: {
        type: 'validation_error',
        correlation_id: 'abc-123',
      },
      status: 422,
    };
    const result = getUserFriendlyErrorMessage(error);
    expect(result).toBe('Please check your input and try again.');
  });

  it('uses canonical error type for unauthorized errors', () => {
    const error = {
      message: 'Access denied',
      error: {
        type: 'unauthorized',
        correlation_id: 'def-456',
      },
      status: 401,
    };
    const result = getUserFriendlyErrorMessage(error);
    expect(result).toBe('Please log in to continue.');
  });

  it('falls back to message patterns when no canonical type', () => {
    const error = {
      message: 'Username or email already exists',
      status: 409,
    };
    const result = getUserFriendlyErrorMessage(error);
    expect(result).toBe(
      'An account with this email or username already exists.'
    );
  });

  it('handles backend error format with details', () => {
    const error = {
      success: false,
      message: 'Username or email already exists',
      error: {
        correlation_id: 'abc-123',
        type: 'domain_error',
      },
    };
    const result = getUserFriendlyErrorMessage(error, { action: 'register' });
    expect(result).toBe(
      'An account with this email or username already exists. Please try logging in instead.'
    );
  });

  it('sanitizes technical error messages', () => {
    const error = {
      message: 'Database connection failed at line 42 in user.py',
      status: 500,
    };
    const result = getUserFriendlyErrorMessage(error);
    expect(result).toBe(
      'Something went wrong on our end. Please try again in a few moments.'
    );
  });

  it('handles network errors', () => {
    const error = new Error('Failed to fetch');
    const result = getUserFriendlyErrorMessage(error);
    expect(result).toBe(
      'Unable to connect. Please check your internet connection and try again.'
    );
  });

  it('provides fallback for unknown errors', () => {
    const result = getUserFriendlyErrorMessage({});
    expect(result).toBe('An unexpected error occurred. Please try again.');
  });

  it('adds context for login errors', () => {
    const error = {
      message: 'Incorrect username or password',
      status: 401,
    };
    const result = getUserFriendlyErrorMessage(error, { action: 'login' });
    expect(result).toBe('Invalid username or password. Please try again.');
  });

  it('adds field context for validation errors', () => {
    const error = {
      message: 'Field validation failed',
      status: 422,
    };
    const result = getUserFriendlyErrorMessage(error, { field: 'email' });
    expect(result).toBe('Please check your input and try again.');
  });
});

describe('shouldLogoutOnError', () => {
  it('returns true for canonical unauthorized error type', () => {
    const error = {
      error: { type: 'unauthorized' },
      status: 401,
    };
    expect(shouldLogoutOnError(error)).toBe(true);
  });

  it('returns true for canonical token_expired error type', () => {
    const error = {
      error: { type: 'token_expired' },
      status: 401,
    };
    expect(shouldLogoutOnError(error)).toBe(true);
  });

  it('returns true for 401 errors', () => {
    const error = { status: 401 };
    expect(shouldLogoutOnError(error)).toBe(true);
  });

  it('returns true for token expired messages', () => {
    const error = { message: 'Your session has expired' };
    expect(shouldLogoutOnError(error)).toBe(true);
  });

  it('returns false for other errors', () => {
    const error = { status: 400, message: 'Bad request' };
    expect(shouldLogoutOnError(error)).toBe(false);
  });

  it('returns false for non-error objects', () => {
    expect(shouldLogoutOnError('some string')).toBe(false);
    expect(shouldLogoutOnError(null)).toBe(false);
    expect(shouldLogoutOnError(undefined)).toBe(false);
  });
});

describe('getRetryBehavior', () => {
  it('allows retry for server errors', () => {
    const error = { status: 500 };
    const result = getRetryBehavior(error);
    expect(result.canRetry).toBe(true);
    expect(result.maxRetries).toBe(2);
    expect(result.suggestedDelay).toBe(1000);
  });

  it('allows retry for service unavailable', () => {
    const error = { status: 503 };
    const result = getRetryBehavior(error);
    expect(result.canRetry).toBe(true);
    expect(result.maxRetries).toBe(3);
    expect(result.suggestedDelay).toBe(2000);
  });

  it('allows retry with longer delay for rate limiting', () => {
    const error = { status: 429 };
    const result = getRetryBehavior(error);
    expect(result.canRetry).toBe(true);
    expect(result.maxRetries).toBe(3);
    expect(result.suggestedDelay).toBe(5000);
  });

  it('does not allow retry for client errors', () => {
    const error = { status: 400 };
    const result = getRetryBehavior(error);
    expect(result.canRetry).toBe(false);
  });

  it('does not allow retry for auth errors', () => {
    const error = { status: 401 };
    const result = getRetryBehavior(error);
    expect(result.canRetry).toBe(false);
  });

  it('handles non-error objects', () => {
    const result = getRetryBehavior('not an error');
    expect(result.canRetry).toBe(false);
  });
});
