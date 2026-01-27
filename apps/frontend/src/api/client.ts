import { logger } from '../lib/logger';
import { useAuthStore } from '../stores/useAuthStore';
import type { ApiResponse, HealthCheckResponse } from '../types/api';
import { ApiErrorImpl } from '../types/api';
import {
  getUserFriendlyErrorMessage,
  shouldLogoutOnError,
} from '../utils/errorMessages';
// API configuration
const API_BASE_URL = getApiBaseUrl();

export function getApiBaseUrl(): string {
  // 1. Explicit build-time override wins (useful for staging/CDN or dev containers)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // 2. Local development + test runner: talk to backend dev server directly
  if (
    import.meta.env.MODE === 'development' ||
    import.meta.env.MODE === 'test'
  ) {
    return 'http://localhost:8000';
  }

  // 3. Production fallback: rely on SAME-ORIGIN reverse proxy routing.
  // We intentionally return an empty string so that requests become
  //   fetch('/api/v1/...')
  // which the browser resolves against the current origin (scheme + host + port).
  // This removes the need to embed hostnames/IPs at build time, avoids CORS & CSP
  // complications, and makes the image environment-agnostic (works under any domain
  // or internal IP as long as the reverse proxy forwards /api/ to the backend).
  // NOTE: If you ever deploy frontend & backend on DIFFERENT origins, set VITE_API_URL.
  return '';
}

// API client with proper error handling
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeaders(): Record<string, string> {
    const token = useAuthStore.getState().token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    // Ensure endpoint starts with /
    const normalizedEndpoint = endpoint.startsWith('/')
      ? endpoint
      : `/${endpoint}`;
    const url = `${this.baseUrl}${normalizedEndpoint}`;

    // Determine if this endpoint should skip logout on 401
    // Auth endpoints: 401 means wrong credentials, not session expiry
    // Draft endpoints with token param: 401 means expired draft token, not session expiry
    // Owner draft endpoints (/me): 401 means draft expired or ownership mismatch, not session expiry
    const isAuthEndpoint = normalizedEndpoint.startsWith('/api/v1/auth/');
    const isDraftTokenEndpoint = (() => {
      if (!normalizedEndpoint.startsWith('/api/v1/ai/drafts/')) {
        return false;
      }
      const queryIndex = normalizedEndpoint.indexOf('?');
      if (queryIndex === -1) {
        return false;
      }
      const query = normalizedEndpoint.slice(queryIndex + 1);
      const params = new URLSearchParams(query);
      return params.has('token');
    })();
    // Owner draft endpoint pattern: /api/v1/ai/drafts/{uuid}/me
    const isOwnerDraftEndpoint = /^\/api\/v1\/ai\/drafts\/[^/]+\/me/.test(
      normalizedEndpoint
    );
    const shouldSkipLogoutOn401 =
      isAuthEndpoint || isDraftTokenEndpoint || isOwnerDraftEndpoint;

    // Avoid logging bearer-like draft tokens in query parameters
    const safeUrlForLogging = isDraftTokenEndpoint ? url.split('?')[0] : url;

    logger.debug(
      `API Request: ${options?.method || 'GET'} ${safeUrlForLogging}`
    );

    try {
      const headers = {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...(options?.headers || {}),
      };
      const resp = await fetch(url, {
        ...options,
        headers,
      });

      logger.debug(`API Response status: ${resp.status}`);
      const responseText = await resp.text();
      logger.debug(`API Response text: ${responseText}`);

      let body;
      try {
        body = responseText ? JSON.parse(responseText) : {};
      } catch (e) {
        logger.error('Failed to parse JSON response:', e);
        // Network/parsing errors - throw as native Error for network issues
        throw new Error(`Invalid JSON response from API: ${responseText}`);
      }

      // Check if user was logged in before processing any errors
      // This is used to determine if a 401 should trigger "session expired" message
      // (only if the user actually had a session)
      const wasLoggedIn = useAuthStore.getState().token !== null;

      if (!resp.ok) {
        // Always throw ApiErrorImpl for HTTP/API-level errors to ensure consistent error handling
        let rawMessage: string = '';
        if (body && typeof body === 'object') {
          const candidate =
            (body as any).message ||
            (body as any).detail ||
            (body as any).error?.message ||
            '';
          rawMessage =
            typeof candidate === 'string'
              ? candidate
              : JSON.stringify(candidate);
        } else if (typeof body === 'string') {
          rawMessage = body;
        }

        let thrownMessage = rawMessage;
        if (!thrownMessage || thrownMessage.trim() === '') {
          thrownMessage = `Request failed (${resp.status})`;
        }

        // Check if this error should trigger logout before throwing
        // Skip logout for endpoints where 401 means something other than session expiry
        // Also skip if the user wasn't logged in - a 401 for an unauthenticated request
        // is expected behavior, not a session expiration
        if (
          wasLoggedIn &&
          !shouldSkipLogoutOn401 &&
          shouldLogoutOnError(body, resp.status)
        ) {
          // Log logout event with correlation ID for debugging
          const correlationId = (body as any)?.error?.correlation_id;
          if (correlationId) {
            logger.info(
              `Session expired logout triggered (correlation_id: ${correlationId})`
            );
          } else {
            logger.info('Session expired logout triggered (no correlation_id)');
          }
          useAuthStore.getState().logout('expired');
        }

        // Always throw ApiErrorImpl for API errors - consistent error contract
        const canonicalCodeSafe = extractCanonicalErrorCode(body);
        throw new ApiErrorImpl(
          thrownMessage,
          resp.status,
          canonicalCodeSafe,
          body as unknown
        );
      }

      // Handle wrapped API responses
      if (body && typeof body === 'object' && 'success' in body) {
        // This is a wrapped ApiResponse
        const apiResponse = body as ApiResponse<T>;

        if (!apiResponse.success) {
          // Prefer raw message from wrapped response when available
          const rawMessage =
            apiResponse.message || apiResponse.error?.message || '';
          const rawMessageStr =
            typeof rawMessage === 'string'
              ? rawMessage
              : JSON.stringify(rawMessage);
          const thrownMessage =
            rawMessageStr && rawMessageStr.trim() !== ''
              ? rawMessageStr
              : `Request failed (${resp.status})`;

          // Skip logout for endpoints where 401 means something other than session expiry
          // Also skip if the user wasn't logged in - a 401 for an unauthenticated request
          // is expected behavior, not a session expiration
          if (
            wasLoggedIn &&
            !shouldSkipLogoutOn401 &&
            shouldLogoutOnError(apiResponse, resp.status)
          ) {
            // Log logout event with correlation ID for debugging
            const correlationId = (apiResponse as any)?.error?.correlation_id;
            if (correlationId) {
              logger.info(
                `Session expired logout triggered (correlation_id: ${correlationId})`
              );
            } else {
              logger.info(
                'Session expired logout triggered (no correlation_id)'
              );
            }
            useAuthStore.getState().logout('expired');
          }

          // Consistent error type for wrapped API responses
          const canonicalCodeSafe = extractCanonicalErrorCode(apiResponse);
          throw new ApiErrorImpl(
            thrownMessage,
            resp.status,
            canonicalCodeSafe,
            apiResponse as unknown
          );
        }

        return apiResponse.data as T;
      }

      // Fallback for non-wrapped responses (e.g., health check)
      return body as T;
    } catch (err: unknown) {
      // Re-throw ApiErrorImpl as-is to maintain consistent error contract
      if (err instanceof ApiErrorImpl) {
        throw err;
      }

      // For native errors (network failures, JSON parsing), wrap them in ApiErrorImpl
      // to ensure callers always receive the same error type
      if (err instanceof Error) {
        logger.error(`Network/parsing error for ${url}: ${err.message}`);
        throw new ApiErrorImpl(
          `Network error: ${err.message}`,
          undefined,
          undefined,
          undefined,
          err
        );
      }

      // Fallback: wrap unknown error shapes into ApiErrorImpl with a user-friendly message
      const friendlyMessage = getUserFriendlyErrorMessage(err);
      const apiError = new ApiErrorImpl(
        friendlyMessage,
        undefined,
        undefined,
        undefined,
        err instanceof Error ? err : undefined
      );

      logger.error(`API request failed: ${url}`, apiError);
      throw apiError;
    }
  }

  // Health check endpoint
  async healthCheck(): Promise<HealthCheckResponse> {
    return this.request<HealthCheckResponse>('/api/v1/health');
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL);

/**
 * Extract a canonical error code (backend canonical error type) from a variety
 * of possible error envelope shapes in a type-safe way.
 */
function extractCanonicalErrorCode(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') return undefined;
  const container: any = body;
  const rawCanonical = container?.error?.type ?? container?.code;
  return typeof rawCanonical === 'string' ? rawCanonical : undefined;
}
