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
  response?: unknown; // Store original response for debugging
  originalError?: Error; // Store original error if wrapped

  constructor(
    message: string, 
    status?: number, 
    response?: unknown, 
    originalError?: Error
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.response = response;
    this.originalError = originalError;
    
    // Extract code from response if available  
    if (response && typeof response === 'object' && response !== null) {
      const responseObj = response as any;
      this.code = responseObj.error?.type || responseObj.code;
    }
  }
}
