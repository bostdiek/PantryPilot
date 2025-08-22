import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../../stores/useAuthStore';
import type { AuthState } from '../../types/Auth';
import { apiClient } from '../client';

// Mock the auth store's getState to control token presence
vi.mock('../../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: vi.fn(() => ({ token: null })),
  },
}));

describe('ApiClient (unit)', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', fetchMock);
  });

  it('sends correct headers and returns data on success', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: { hello: 'world' } }),
    });

    const res = await apiClient.request('/test', { method: 'GET' });
    expect(res).toEqual({ hello: 'world' });
    expect(fetchMock).toHaveBeenCalled();
  });

  it('includes Authorization header when token exists', async () => {
    // make getState return a token
    vi.mocked(useAuthStore.getState).mockReturnValueOnce({
      token: 'tok',
    } as unknown as AuthState);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: {} }),
    });

    await apiClient.request('/secure');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/secure'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer tok' }),
      })
    );
  });
});
