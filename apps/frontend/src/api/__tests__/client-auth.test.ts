import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiClient } from '../client';
import { useAuthStore } from '../../stores/useAuthStore';

// Mock the auth store
vi.mock('../../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: vi.fn(),
  },
}));

// Mock the toast utilities to avoid side effects
vi.mock('../../components/ui/toast-utils', () => ({
  addToast: vi.fn(),
  generateToastId: vi.fn(() => 'test-toast-id'),
}));

describe('ApiClient Authentication Handling', () => {
  const mockLogout = vi.fn();
  const mockGetState = vi.mocked(useAuthStore.getState);

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();
    mockGetState.mockReturnValue({
      token: 'test-token',
      user: null,
      hasHydrated: true,
      login: vi.fn(),
      logout: mockLogout,
      setToken: vi.fn(),
      setUser: vi.fn(),
      getDisplayName: vi.fn(() => 'Test User'),
    });

    // Mock fetch globally
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calls logout with "expired" reason on 401 HTTP status with backend detail message', async () => {
    // Setup mock response for 401 with backend's standard "Could not validate credentials" message
    const mockResponse = {
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Could not validate credentials' })),
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    // Make the request and expect it to throw
    await expect(apiClient.request('/test')).rejects.toThrow();

    // Verify logout was called with 'expired' reason
    expect(mockLogout).toHaveBeenCalledWith('expired');
  });

  it('calls logout with "expired" reason on 401 with canonical error envelope', async () => {
    // Setup mock response for 401 with canonical error structure from updated backend
    const mockResponse = {
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({
        success: false,
        message: 'An HTTP error occurred',
        error: {
          type: 'unauthorized',
          correlation_id: 'test-123'
        }
      })),
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    // Make the request and expect it to throw
    await expect(apiClient.request('/test')).rejects.toThrow();

    // Verify logout was called with 'expired' reason
    expect(mockLogout).toHaveBeenCalledWith('expired');
  });

  it('does not call logout on non-401 errors', async () => {
    // Setup mock response for 500 error
    const mockResponse = {
      ok: false,
      status: 500,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Internal server error' })),
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    // Make the request and expect it to throw
    await expect(apiClient.request('/test')).rejects.toThrow();

    // Verify logout was NOT called
    expect(mockLogout).not.toHaveBeenCalled();
  });

  it('calls logout for wrapped API response with 401 status', async () => {
    // Setup mock response for wrapped API failure with 401
    const mockResponse = {
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({
        success: false,
        data: null,
        message: 'Authentication failed',
        error: {
          type: 'unauthorized',
          correlation_id: 'test-456'
        }
      })),
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    // Make the request and expect it to throw
    await expect(apiClient.request('/test')).rejects.toThrow();

    // Verify logout was called with 'expired' reason
    expect(mockLogout).toHaveBeenCalledWith('expired');
  });

  it('prioritizes 401 HTTP status over non-auth canonical error types', async () => {
    // Setup response with 401 status but non-auth error type
    const mockResponse = {
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({
        success: false,
        error: {
          type: 'validation_error', // non-auth type
          message: 'Some validation error'
        }
      })),
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    // Make the request and expect it to throw
    await expect(apiClient.request('/test')).rejects.toThrow();

    // Verify logout was still called because HTTP status is 401
    expect(mockLogout).toHaveBeenCalledWith('expired');
  });

  it('handles successful requests without calling logout', async () => {
    // Setup mock response for successful request
    const mockResponse = {
      ok: true,
      status: 200,
      text: () => Promise.resolve(JSON.stringify({ data: { hello: 'world' } })),
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    // Make the request
    const result = await apiClient.request('/test');

    // Verify the response
    expect(result).toEqual({ data: { hello: 'world' } });

    // Verify logout was NOT called
    expect(mockLogout).not.toHaveBeenCalled();
  });
});