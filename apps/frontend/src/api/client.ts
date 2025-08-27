import { useAuthStore } from '../stores/useAuthStore';
import type { ApiError, ApiResponse, HealthCheckResponse } from '../types/api';
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
        throw new Error(`Invalid JSON response from API: ${responseText}`);
      }

      if (!resp.ok) {
        const apiError: ApiError = {
          message: body.message ?? `Request failed (${resp.status})`,
          status: resp.status,
        };
        throw apiError;
      }

      // Handle wrapped API responses
      if (body && typeof body === 'object' && 'success' in body) {
        // This is a wrapped ApiResponse
        const apiResponse = body as ApiResponse<T>;

        if (!apiResponse.success) {
          const apiError: ApiError = {
            message: apiResponse.message ?? 'Request failed',
            status: resp.status,
          };
          throw apiError;
        }

        return apiResponse.data as T;
      }

      // Fallback for non-wrapped responses (e.g., health check)
      return body as T;
    } catch (err: unknown) {
      const apiError: ApiError =
        err instanceof Error
          ? { message: err.message }
          : { message: 'Unknown error' };
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
