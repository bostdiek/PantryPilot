// API Response Types
export interface ApiResponse<T = unknown> {
  data?: T;
  message?: string;
  error?: string;
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
