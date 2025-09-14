import { useAuthStore } from '../stores/useAuthStore';
import type { ApiResponse, HealthCheckResponse } from '../types/api';
import { ApiErrorImpl } from '../types/api';
import {
  getUserFriendlyErrorMessage,
  shouldLogoutOnError,
} from '../utils/errorMessages';
// API configuration
const API_BASE_URL = getApiBaseUrl();

function getApiBaseUrl(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (
    import.meta.env.MODE === 'development' ||
    import.meta.env.MODE === 'test'
  ) {
    return 'http://localhost:8000';
  }
  throw new Error('VITE_API_URL must be set in production environments');
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

    console.log(`API Request: ${options?.method || 'GET'} ${url}`);

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

      console.log(`API Response status: ${resp.status}`);
      const responseText = await resp.text();
      console.log(`API Response text:`, responseText);

      let body;
      try {
        body = responseText ? JSON.parse(responseText) : {};
      } catch (e) {
        console.error('Failed to parse JSON response:', e);
        // Network/parsing errors - throw as native Error for network issues
        throw new Error(`Invalid JSON response from API: ${responseText}`);
      }

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
        if (shouldLogoutOnError(body)) {
          useAuthStore.getState().logout();
        }

        // Always throw ApiErrorImpl for API errors - consistent error contract
        // Extract canonical error code if present in the body and coerce types safely
        const rawCanonical = (body as any)?.error?.type ?? (body as any)?.code;
        const canonicalCodeSafe: string | undefined =
          typeof rawCanonical === 'string' ? rawCanonical : undefined;
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

          if (shouldLogoutOnError(apiResponse)) {
            useAuthStore.getState().logout();
          }

          // Consistent error type for wrapped API responses
          const rawCanonical =
            (apiResponse as any)?.error?.type ?? (apiResponse as any)?.code;
          const canonicalCodeSafe: string | undefined =
            typeof rawCanonical === 'string' ? rawCanonical : undefined;
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
        console.error(`Network/parsing error for ${url}:`, err.message);
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

      console.error(`API request failed: ${url}`, apiError);
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
