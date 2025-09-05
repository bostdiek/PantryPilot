// API Response Types
export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  message: string;
  error?: Record<string, unknown> | null;
}

// Health Check Types
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  message: string;
  timestamp?: string;
}

// Common API Error Type
export interface ApiError {
  message: string;
  status?: number;
  code?: string;
}

// Concrete error implementation for robust runtime checks
export class ApiErrorImpl extends Error implements ApiError {
  status?: number;
  code?: string;
  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}
