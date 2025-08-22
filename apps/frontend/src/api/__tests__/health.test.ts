import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '../client';
import { healthCheck } from '../endpoints/health';

// Mock the apiClient
vi.mock('../client', () => ({
  apiClient: {
    request: vi.fn(),
  },
}));

describe('Health API Endpoint', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call apiClient.request with correct path and method', async () => {
    // Mock the request method to return a successful response
    vi.mocked(apiClient.request).mockResolvedValueOnce({
      status: 'healthy',
      message: 'API is operational',
      timestamp: '2025-08-22T12:34:56Z',
    });

    const result = await healthCheck();

    expect(apiClient.request).toHaveBeenCalledWith('/api/v1/health', {
      method: 'GET',
    });

    expect(result).toEqual({
      status: 'healthy',
      message: 'API is operational',
      timestamp: '2025-08-22T12:34:56Z',
    });
  });

  it('should propagate errors from apiClient', async () => {
    // Mock the request method to throw an error
    vi.mocked(apiClient.request).mockRejectedValueOnce({
      message: 'Network error',
    });

    await expect(healthCheck()).rejects.toEqual({
      message: 'Network error',
    });
  });
});
