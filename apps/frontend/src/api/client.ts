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

      const body = (await resp.json()) as ApiResponse<T>;
      if (!resp.ok || body.error) {
        const apiError: ApiError = {
          message: body.error ?? `Request failed (${resp.status})`,
          status: resp.status,
        };
        throw apiError;
      }

      return body.data as T;
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
  async healthCheck(): Promise<ApiResponse<HealthCheckResponse>> {
  async healthCheck(): Promise<HealthCheckResponse> {
    return this.request<HealthCheckResponse>('/api/v1/health');
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL);
