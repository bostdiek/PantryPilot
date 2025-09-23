/**
 * User-friendly error message mapping and sanitization.
 *
 * This module provides:
 * - Mapping of backend error codes to user-friendly messages
 * - Sanitization of error messages to prevent technical details leakage
 * - Fallback error messages for unknown error types
 * - Context-aware error messaging based on user actions
 */

// Canonical error type mappings from backend
const ERROR_TYPE_MESSAGES = {
  // Backend error types (canonical)
  http_error: 'Request failed. Please try again.',
  validation_error: 'Please check your input and try again.',
  domain_error: 'A business logic error occurred.',
  integrity_error: 'This item already exists.',
  internal_error:
    'Something went wrong on our end. Please try again in a few moments.',

  // Authentication error types
  unauthorized: 'Please log in to continue.',
  forbidden: "You don't have permission to perform this action.",
  token_expired: 'Your session has expired. Please log in again.',
  invalid_credentials: 'Invalid username or password.',

  // User management error types
  user_exists: 'An account with this email or username already exists.',
  user_not_found: 'User not found.',

  // Network error types
  network_error:
    'Unable to connect. Please check your internet connection and try again.',
  service_unavailable:
    'The service is temporarily unavailable. Please try again later.',
  too_many_requests: 'Too many requests. Please wait a moment and try again.',
} as const;

// User-friendly error messages for common scenarios (fallbacks)
const ERROR_MESSAGES = {
  // Authentication & Authorization
  UNAUTHORIZED: 'Please log in to continue.',
  FORBIDDEN: "You don't have permission to perform this action.",
  TOKEN_EXPIRED: 'Your session has expired. Please log in again.',

  // Validation Errors
  VALIDATION_ERROR: 'Please check your input and try again.',
  REQUIRED_FIELD: 'Please fill in all required fields.',
  INVALID_EMAIL: 'Please enter a valid email address.',
  INVALID_PASSWORD: 'Password must be at least 12 characters long.',

  // User Management
  USER_EXISTS: 'An account with this email or username already exists.',
  USER_NOT_FOUND: 'User not found.',
  INVALID_CREDENTIALS: 'Invalid username or password.',

  // Network & Server Errors
  NETWORK_ERROR:
    'Unable to connect. Please check your internet connection and try again.',
  SERVER_ERROR:
    'Something went wrong on our end. Please try again in a few moments.',
  SERVICE_UNAVAILABLE:
    'The service is temporarily unavailable. Please try again later.',

  // Resource Errors
  NOT_FOUND: 'The requested item could not be found.',
  ALREADY_EXISTS: 'This item already exists.',
  TOO_MANY_REQUESTS: 'Too many requests. Please wait a moment and try again.',

  // Generic Fallbacks
  UNKNOWN_ERROR: 'An unexpected error occurred. Please try again.',
  REQUEST_FAILED: 'Request failed. Please try again.',
} as const;

// Common error patterns to match against backend messages
const ERROR_PATTERNS = [
  // Authentication patterns
  { pattern: /unauthorized|401/i, key: 'UNAUTHORIZED' },
  { pattern: /forbidden|403/i, key: 'FORBIDDEN' },
  { pattern: /token.*expired|session.*expired/i, key: 'TOKEN_EXPIRED' },
  {
    pattern: /invalid.*credentials|incorrect.*username.*password/i,
    key: 'INVALID_CREDENTIALS',
  },

  // Validation patterns
  {
    pattern: /validation.*failed|invalid.*request.*data/i,
    key: 'VALIDATION_ERROR',
  },
  { pattern: /field.*required|missing.*field/i, key: 'REQUIRED_FIELD' },
  { pattern: /invalid.*email|email.*invalid/i, key: 'INVALID_EMAIL' },
  { pattern: /password.*short|password.*length/i, key: 'INVALID_PASSWORD' },

  // User management patterns
  {
    pattern: /user.*already.*exists|username.*email.*already.*exists/i,
    key: 'USER_EXISTS',
  },
  { pattern: /user.*not.*found/i, key: 'USER_NOT_FOUND' },

  // Network patterns
  {
    pattern: /network.*error|failed.*to.*fetch|connection.*error/i,
    key: 'NETWORK_ERROR',
  },
  { pattern: /internal.*server.*error|500/i, key: 'SERVER_ERROR' },
  { pattern: /service.*unavailable|503/i, key: 'SERVICE_UNAVAILABLE' },
  { pattern: /too.*many.*requests|429/i, key: 'TOO_MANY_REQUESTS' },

  // Resource patterns
  { pattern: /not.*found|404/i, key: 'NOT_FOUND' },
  { pattern: /already.*exists|409/i, key: 'ALREADY_EXISTS' },
] as const;

export interface ErrorContext {
  action?: string; // e.g., 'login', 'register', 'create_recipe'
  resource?: string; // e.g., 'user', 'recipe', 'meal_plan'
  field?: string; // e.g., 'email', 'password', 'title'
}

/**
 * Get a user-friendly error message from a backend error.
 *
 * @param error - The error object or message from the backend
 * @param context - Optional context about what the user was trying to do
 * @returns A user-friendly error message
 */
export function getUserFriendlyErrorMessage(
  error: unknown,
  context?: ErrorContext
): string {
  let rawMessage = '';
  let statusCode: number | undefined;
  let errorType: string | undefined;

  // Extract message and error type from different error formats
  if (typeof error === 'string') {
    rawMessage = error;
  } else if (error && typeof error === 'object') {
    const errorObj = error as any;

    // Try to get status code
    statusCode = errorObj.status || errorObj.statusCode;

    // Try to get canonical error type first (preferred approach)
    errorType = errorObj.error?.type;

    // Try different message fields
    rawMessage =
      errorObj.message || errorObj.detail || errorObj.error?.message || '';
  }

  // Prioritize canonical error type mapping (machine-friendly)
  // We only early-return for canonical types that are already specific and
  // user-friendly. Very generic canonical types (currently only 'domain_error')
  // fall through so that message-pattern heuristics (e.g. "already exists") and
  // context-aware fallbacks (like registration flows) can produce a more precise
  // message. If additional generic types are introduced later they can be added
  // to the GENERIC_CANONICAL_TYPES set without changing the logic structure.
  const GENERIC_CANONICAL_TYPES = new Set<string>(['domain_error']);
  if (errorType && errorType in ERROR_TYPE_MESSAGES) {
    if (!GENERIC_CANONICAL_TYPES.has(errorType)) {
      const canonicalMessage =
        ERROR_TYPE_MESSAGES[errorType as keyof typeof ERROR_TYPE_MESSAGES];
      return addContextToErrorMessage(canonicalMessage, context);
    }
    // Intentional fall-through for generic canonical types.
  }

  // Coerce non-string raw messages into safe strings for sanitization.
  rawMessage = coerceToString(rawMessage);

  // Sanitize the raw message (remove technical details)
  const sanitizedMessage = sanitizeErrorMessage(rawMessage);

  // Try to map to user-friendly message using patterns (fallback)
  const userFriendlyMessage = mapErrorMessage(sanitizedMessage, statusCode);

  // Add context-specific messaging if available
  if (context) {
    // Extract registration-specific fallback logic to a helper for clarity and
    // easier unit-testing. This avoids entangling test heuristics with the main
    // mapping logic and keeps this function focused on selecting a message.
    if (context.action === 'register') {
      const regFallback = getRegisterFallbackMessage(
        sanitizedMessage,
        statusCode
      );
      if (regFallback) return regFallback;
    }

    return addContextToErrorMessage(userFriendlyMessage, context);
  }

  return userFriendlyMessage;
}

/**
 * Sanitize error message by removing technical details and sensitive information.
 */
function sanitizeErrorMessage(message: string): string {
  if (!message) return '';

  // Remove common technical patterns
  const technicalPatterns = [
    /\b(stack trace|traceback|exception in thread).*$/is,
    /\b(at [a-zA-Z0-9_.]+\([^)]*\))/g, // Stack trace lines
    /\b[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}\b/g, // UUIDs
    /\b(correlation[_-]?id|request[_-]?id):\s*[a-fA-F0-9-]+/gi,
    /\b(sql|database|query).*error.*$/gi,
    /\b(internal|system).*error.*$/gi,
  ];

  let sanitized = message;

  technicalPatterns.forEach((pattern) => {
    sanitized = sanitized.replace(pattern, '');
  });

  return sanitized.trim();
}

/**
 * Coerce an unknown value into a safe string for error display.
 * Empty objects become an empty string; non-serializable values fall back to String().
 */
export function coerceToString(value: unknown): string {
  if (typeof value === 'string') return value;
  if (value == null) return '';
  if (typeof value === 'object') {
    try {
      // Treat empty objects as no-message
      if (Object.keys(value as Record<string, unknown>).length === 0) return '';
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

/**
 * Registration-specific fallback messaging extracted for clarity and testability.
 * Returns a string message when a specialized fallback applies, otherwise undefined.
 */
export function getRegisterFallbackMessage(
  message: string,
  statusCode?: number
): string | undefined {
  const lowerMsg = (message || '').toLowerCase();

  if (statusCode === 422) {
    if (lowerMsg.includes('validation') || lowerMsg.includes('field')) {
      return ERROR_MESSAGES.VALIDATION_ERROR;
    }
    return 'Invalid registration data. Please check your inputs.';
  }

  if (statusCode && statusCode >= 500) {
    return 'Registration failed. Please try again.';
  }

  if (
    lowerMsg.includes('username') &&
    lowerMsg.includes('email') &&
    lowerMsg.includes('already')
  ) {
    return 'An account with this email or username already exists. Please try logging in instead.';
  }

  if (lowerMsg.includes('username') && lowerMsg.includes('already')) {
    return 'Username is already taken';
  }
  if (lowerMsg.includes('email') && lowerMsg.includes('already')) {
    return 'Email is already registered';
  }

  return undefined;
}

/**
 * Map error message to user-friendly equivalent using patterns.
 */
function mapErrorMessage(message: string, statusCode?: number): string {
  // First, try to match by message content (more specific)
  for (const { pattern, key } of ERROR_PATTERNS) {
    if (pattern.test(message)) {
      return ERROR_MESSAGES[key as keyof typeof ERROR_MESSAGES];
    }
  }

  // Then, try to match by status code (fallback)
  if (statusCode) {
    switch (statusCode) {
      case 400:
        return ERROR_MESSAGES.VALIDATION_ERROR;
      case 401:
        return ERROR_MESSAGES.UNAUTHORIZED;
      case 403:
        return ERROR_MESSAGES.FORBIDDEN;
      case 404:
        return ERROR_MESSAGES.NOT_FOUND;
      case 409:
        return ERROR_MESSAGES.ALREADY_EXISTS;
      case 422:
        return ERROR_MESSAGES.VALIDATION_ERROR;
      case 429:
        return ERROR_MESSAGES.TOO_MANY_REQUESTS;
      case 500:
      case 502:
      case 503:
      case 504:
        return ERROR_MESSAGES.SERVER_ERROR;
    }
  }

  // If no pattern matches, return sanitized message or fallback
  return message || ERROR_MESSAGES.UNKNOWN_ERROR;
}

/**
 * Add context-specific information to error messages.
 */
function addContextToErrorMessage(
  message: string,
  context?: ErrorContext
): string {
  const { action, field } = context || {};

  // Add action context
  if (action) {
    switch (action) {
      case 'login':
        if (message.includes('Invalid') || message.includes('credentials')) {
          return 'Invalid username or password. Please try again.';
        }
        break;
      case 'register':
        if (message.includes('already exists')) {
          return 'An account with this email or username already exists. Please try logging in instead.';
        }
        break;
      case 'create_recipe':
        if (message.includes('validation')) {
          return 'Please check your recipe details and try again.';
        }
        break;
    }
  }

  // Add field context
  if (field) {
    if (message.includes('validation') || message.includes('invalid')) {
      return `Please check the ${field} field and try again.`;
    }
  }

  return message;
}

/**
 * Check if an error should trigger a logout (e.g., token expired).
 */
export function shouldLogoutOnError(error: unknown, httpStatus?: number): boolean {
  // Primary check: HTTP status code from response (most reliable)
  if (httpStatus === 401) {
    return true;
  }

  // Early return if no error to analyze further
  if (!error) {
    return false;
  }

  // Second check: canonical error types (machine-readable)
  if (error && typeof error === 'object') {
    const errorObj = error as any;
    const errorType = errorObj.error?.type;

    // Use canonical error types when available
    if (errorType === 'unauthorized' || errorType === 'token_expired') {
      return true;
    }

    // Fallback: check HTTP status code embedded in error object (legacy)
    const status = errorObj.status || errorObj.statusCode;
    if (status === 401) {
      return true;
    }
  }

  // Last resort: fallback to message content analysis
  const message = getUserFriendlyErrorMessage(error);
  return (
    message.includes('session has expired') ||
    message.includes('log in to continue')
  );
}

/**
 * Get appropriate retry behavior for an error.
 */
export function getRetryBehavior(error: unknown): {
  canRetry: boolean;
  suggestedDelay?: number;
  maxRetries?: number;
} {
  if (!error || typeof error !== 'object') {
    return { canRetry: false };
  }

  const statusCode = (error as any).status;

  switch (statusCode) {
    case 408: // Request Timeout
    case 429: // Too Many Requests
    case 502: // Bad Gateway
    case 503: // Service Unavailable
    case 504: // Gateway Timeout
      return {
        canRetry: true,
        suggestedDelay: statusCode === 429 ? 5000 : 2000,
        maxRetries: 3,
      };

    case 500: // Internal Server Error
      return {
        canRetry: true,
        suggestedDelay: 1000,
        maxRetries: 2,
      };

    default:
      return { canRetry: false };
  }
}
