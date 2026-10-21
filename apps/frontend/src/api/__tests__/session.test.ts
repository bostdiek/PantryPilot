import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../../stores/useAuthStore';
import { apiClient } from '../client';

vi.mock('../../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: vi.fn(),
  },
}));

describe('active session renewal', () => {
  const fetchMock = vi.fn();
  const setToken = vi.fn();
  const logout = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', fetchMock);
    vi.mocked(useAuthStore.getState).mockReturnValue({
      token: 'expired-access-token',
      user: null,
      hasHydrated: true,
      login: vi.fn(),
      logout,
      setToken,
      setUser: vi.fn(),
      getDisplayName: vi.fn(() => 'Cook'),
    });
  });

  it('renews once and retries an unauthorized write once', async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () =>
          JSON.stringify({ detail: 'Could not validate credentials' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: 'renewed-access-token' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ saved: true }),
      });

    await expect(
      apiClient.request('/api/v1/recipes', {
        method: 'POST',
        body: JSON.stringify({ title: 'Soup' }),
      })
    ).resolves.toEqual({ saved: true });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toContain('/api/v1/auth/refresh');
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      credentials: 'include',
      body: JSON.stringify({ activity: false }),
    });
    expect(setToken).toHaveBeenCalledWith('renewed-access-token');
  });

  it('does not renew for a resource-specific 401', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: async () => JSON.stringify({ detail: 'Recipe is unavailable' }),
    });

    await expect(
      apiClient.request('/api/v1/recipes/42', { method: 'DELETE' })
    ).rejects.toThrow();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(logout).not.toHaveBeenCalled();
  });

  it('coalesces parallel 401s and retries each write only once', async () => {
    let resourceCalls = 0;
    let refreshCalls = 0;
    fetchMock.mockImplementation((input) => {
      if (String(input).includes('/api/v1/auth/refresh')) {
        refreshCalls += 1;
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ access_token: 'renewed-access-token' }),
        });
      }

      resourceCalls += 1;
      if (resourceCalls <= 2) {
        return Promise.resolve({
          ok: false,
          status: 401,
          text: async () =>
            JSON.stringify({ detail: 'Could not validate credentials' }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ accepted: true }),
      });
    });

    const results = await Promise.all([
      apiClient.request('/api/v1/recipes', {
        method: 'POST',
        body: JSON.stringify({ title: 'Soup' }),
      }),
      apiClient.request('/api/v1/mealplans', {
        method: 'POST',
        body: JSON.stringify({ recipe: 'Soup' }),
      }),
    ]);

    expect(results).toEqual([{ accepted: true }, { accepted: true }]);
    expect(refreshCalls).toBe(1);
    expect(resourceCalls).toBe(4);
  });

  it('does not refresh merely because a protected request is polled', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ status: 'ok' }),
    });

    await apiClient.request('/api/v1/recipes');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      credentials: 'include',
    });
  });

  it('logs out without retrying when the server rejects renewal', async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () =>
          JSON.stringify({ detail: 'Could not validate credentials' }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

    await expect(
      apiClient.request('/api/v1/recipes', {
        method: 'POST',
        body: JSON.stringify({ title: 'Soup' }),
      })
    ).rejects.toThrow();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(logout).toHaveBeenCalledWith('expired');
  });
});
