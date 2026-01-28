import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../../stores/useAuthStore';
import { apiClient } from '../client';

// Mock the auth store
vi.mock('../../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: vi.fn(),
  },
}));

// Mock the toast utilities to avoid side effects
vi.mock('../../components/ui/toast-utils', () => ({
  addToast: vi.fn(),
  addToastIfNotExists: vi.fn(),
  generateToastId: vi.fn(() => 'test-toast-id'),
}));

describe('ApiClient Authentication Handling', () => {
  const mockLogout = vi.fn();
  const mockGetState = vi.mocked(useAuthStore.getState);
  const fetchMock = vi.fn();

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();
    vi.stubGlobal('fetch', fetchMock);

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
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calls logout with "expired" reason on 401 HTTP status with backend detail message', async () => {
    // Setup mock response for 401 with backend's standard "Could not validate credentials" message
    const mockResponse = {
      ok: false,
      status: 401,
      text: () =>
        Promise.resolve(
          JSON.stringify({ detail: 'Could not validate credentials' })
        ),
    };
    fetchMock.mockResolvedValue(mockResponse);

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
      text: () =>
        Promise.resolve(
          JSON.stringify({
            success: false,
            message: 'An HTTP error occurred',
            error: {
              type: 'unauthorized',
              correlation_id: 'test-123',
            },
          })
        ),
    };
    fetchMock.mockResolvedValue(mockResponse);

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
      text: () =>
        Promise.resolve(JSON.stringify({ detail: 'Internal server error' })),
    };
    fetchMock.mockResolvedValue(mockResponse);

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
      text: () =>
        Promise.resolve(
          JSON.stringify({
            success: false,
            data: null,
            message: 'Authentication failed',
            error: {
              type: 'unauthorized',
              correlation_id: 'test-456',
            },
          })
        ),
    };
    fetchMock.mockResolvedValue(mockResponse);

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
      text: () =>
        Promise.resolve(
          JSON.stringify({
            success: false,
            error: {
              type: 'validation_error', // non-auth type
              message: 'Some validation error',
            },
          })
        ),
    };
    fetchMock.mockResolvedValue(mockResponse);

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
    fetchMock.mockResolvedValue(mockResponse);

    // Make the request
    const result = await apiClient.request('/test');

    // Verify the response
    expect(result).toEqual({ data: { hello: 'world' } });

    // Verify logout was NOT called
    expect(mockLogout).not.toHaveBeenCalled();
  });

  it('logs out when canonical error type is unauthorized even with non-401 status', async () => {
    // Setup response with canonical unauthorized error type but 200 status in wrapped response
    const mockResponse = {
      ok: true, // But wrapped response indicates failure
      status: 200,
      text: () =>
        Promise.resolve(
          JSON.stringify({
            success: false,
            error: {
              type: 'unauthorized',
              correlation_id: 'test-correlation-123',
            },
          })
        ),
    };
    fetchMock.mockResolvedValue(mockResponse);

    // Make the request and expect it to throw
    await expect(apiClient.request('/test')).rejects.toThrow();

    // Verify logout was called because canonical type indicates auth failure
    expect(mockLogout).toHaveBeenCalledWith('expired');
  });

  it('logs out when token_expired canonical error type is present', async () => {
    // Setup response with token_expired canonical error type
    const mockResponse = {
      ok: false,
      status: 200, // Non-401 status but canonical type should trigger logout
      text: () =>
        Promise.resolve(
          JSON.stringify({
            success: false,
            error: {
              type: 'token_expired',
              correlation_id: 'test-correlation-456',
            },
          })
        ),
    };
    fetchMock.mockResolvedValue(mockResponse);

    // Make the request and expect it to throw
    await expect(apiClient.request('/test')).rejects.toThrow();

    // Verify logout was called for token_expired canonical type
    expect(mockLogout).toHaveBeenCalledWith('expired');
  });

  describe('Draft token endpoints skip logout on 401', () => {
    it('does NOT call logout on 401 for draft token endpoint with token param', async () => {
      // Setup mock response for 401 on a draft token endpoint
      const mockResponse = {
        ok: false,
        status: 401,
        text: () =>
          Promise.resolve(
            JSON.stringify({ detail: 'Draft token expired or invalid' })
          ),
      };
      fetchMock.mockResolvedValue(mockResponse);

      // Make the request to a draft endpoint with token param and expect it to throw
      await expect(
        apiClient.request('/api/v1/ai/drafts/123?token=abc123')
      ).rejects.toThrow();

      // Verify logout was NOT called - draft token 401 should not trigger logout
      expect(mockLogout).not.toHaveBeenCalled();
    });

    it('does NOT call logout on 401 for draft token endpoint with additional query params', async () => {
      // Setup mock response for 401 on a draft token endpoint with multiple params
      const mockResponse = {
        ok: false,
        status: 401,
        text: () =>
          Promise.resolve(
            JSON.stringify({ detail: 'Draft token expired or invalid' })
          ),
      };
      fetchMock.mockResolvedValue(mockResponse);

      // Make the request with multiple query params including token
      await expect(
        apiClient.request('/api/v1/ai/drafts/456?foo=bar&token=xyz789&baz=qux')
      ).rejects.toThrow();

      // Verify logout was NOT called
      expect(mockLogout).not.toHaveBeenCalled();
    });

    it('DOES call logout on 401 for draft endpoint without token param', async () => {
      // Setup mock response for 401 on a draft endpoint accessed via session auth (no token param)
      const mockResponse = {
        ok: false,
        status: 401,
        text: () =>
          Promise.resolve(
            JSON.stringify({ detail: 'Could not validate credentials' })
          ),
      };
      fetchMock.mockResolvedValue(mockResponse);

      // Make the request to draft endpoint without token param
      await expect(
        apiClient.request('/api/v1/ai/drafts/123')
      ).rejects.toThrow();

      // Verify logout WAS called - session auth 401 should trigger logout
      expect(mockLogout).toHaveBeenCalledWith('expired');
    });

    it('DOES call logout on 401 for non-draft endpoints', async () => {
      // Setup mock response for 401 on a regular endpoint
      const mockResponse = {
        ok: false,
        status: 401,
        text: () =>
          Promise.resolve(
            JSON.stringify({ detail: 'Could not validate credentials' })
          ),
      };
      fetchMock.mockResolvedValue(mockResponse);

      // Make the request to a regular endpoint
      await expect(apiClient.request('/api/v1/recipes')).rejects.toThrow();

      // Verify logout WAS called for regular endpoints
      expect(mockLogout).toHaveBeenCalledWith('expired');
    });

    it('does NOT match draft token endpoint for other query params containing "token" substring', async () => {
      // Ensure we only match the exact 'token' param, not 'refresh_token', 'not_token', etc.
      const mockResponse = {
        ok: false,
        status: 401,
        text: () =>
          Promise.resolve(
            JSON.stringify({ detail: 'Could not validate credentials' })
          ),
      };
      fetchMock.mockResolvedValue(mockResponse);

      // Make the request with a param containing 'token' in its name but not 'token' exactly
      await expect(
        apiClient.request('/api/v1/ai/drafts/123?refresh_token=abc123')
      ).rejects.toThrow();

      // Verify logout WAS called - refresh_token should not be treated as draft token
      expect(mockLogout).toHaveBeenCalledWith('expired');
    });
  });

  describe('Unauthenticated user handling (no token)', () => {
    beforeEach(() => {
      // Override the default mock to simulate unauthenticated user
      mockGetState.mockReturnValue({
        token: null, // No token - user is not logged in
        user: null,
        hasHydrated: true,
        login: vi.fn(),
        logout: mockLogout,
        setToken: vi.fn(),
        setUser: vi.fn(),
        getDisplayName: vi.fn(() => 'Guest'),
      });
    });

    it('does NOT call logout on 401 when user was never logged in', async () => {
      // Setup mock response for 401
      const mockResponse = {
        ok: false,
        status: 401,
        text: () =>
          Promise.resolve(
            JSON.stringify({ detail: 'Could not validate credentials' })
          ),
      };
      fetchMock.mockResolvedValue(mockResponse);

      // Make the request and expect it to throw
      await expect(
        apiClient.request('/api/v1/mealplans/weekly')
      ).rejects.toThrow();

      // Verify logout was NOT called - user was never logged in, so no "session expired"
      expect(mockLogout).not.toHaveBeenCalled();
    });

    it('does NOT call logout on 401 with canonical unauthorized error when user was never logged in', async () => {
      // Setup mock response for 401 with canonical error structure
      const mockResponse = {
        ok: false,
        status: 401,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              success: false,
              message: 'Authentication required',
              error: {
                type: 'unauthorized',
                correlation_id: 'test-789',
              },
            })
          ),
      };
      fetchMock.mockResolvedValue(mockResponse);

      // Make the request and expect it to throw
      await expect(apiClient.request('/api/v1/recipes')).rejects.toThrow();

      // Verify logout was NOT called - no session to expire
      expect(mockLogout).not.toHaveBeenCalled();
    });

    it('does NOT call logout on wrapped API 401 when user was never logged in', async () => {
      // Setup mock response for wrapped API failure with 401
      const mockResponse = {
        ok: true, // HTTP OK but API indicates auth failure
        status: 200,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              success: false,
              data: null,
              message: 'Authentication failed',
              error: {
                type: 'unauthorized',
                correlation_id: 'test-999',
              },
            })
          ),
      };
      fetchMock.mockResolvedValue(mockResponse);

      // Make the request and expect it to throw
      await expect(apiClient.request('/test')).rejects.toThrow();

      // Verify logout was NOT called - user was never logged in
      expect(mockLogout).not.toHaveBeenCalled();
    });
  });
});
