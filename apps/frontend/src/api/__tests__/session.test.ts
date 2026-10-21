import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../../stores/useAuthStore';
import { apiClient } from '../client';
import {
  authenticatedFetch,
  cancelSessionActivity,
  markSessionActivity,
  refreshAccessToken,
} from '../session';
import type { AuthState } from '../../types/auth';

function accessToken(
  subject = 'cook-a',
  session = 'session-a',
  generation = 0
) {
  return `header.${btoa(JSON.stringify({ sub: subject, sid: session, generation }))}.signature`;
}

const originalToken = accessToken();
const renewedToken = accessToken('cook-a', 'session-a', 1);

vi.mock('../../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: vi.fn(),
  },
}));

describe('active session renewal', () => {
  const fetchMock = vi.fn();
  const setToken = vi.fn();
  const logout = vi.fn();
  let state: AuthState;

  beforeEach(() => {
    cancelSessionActivity();
    vi.clearAllMocks();
    vi.stubGlobal('fetch', fetchMock);
    state = {
      token: originalToken,
      user: null,
      hasHydrated: true,
      login: vi.fn(),
      logout,
      setToken,
      setUser: vi.fn(),
      getDisplayName: vi.fn(() => 'Cook'),
    };
    setToken.mockImplementation((token: string) => {
      state.token = token;
    });
    logout.mockImplementation(() => {
      state.token = null;
    });
    vi.mocked(useAuthStore.getState).mockImplementation(() => state);
  });

  afterEach(() => {
    cancelSessionActivity();
    vi.useRealTimers();
  });

  it('reports trailing activity before the actual idle boundary', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-21T12:00:00Z'));
    let serverActivityAt = Date.now();
    fetchMock.mockImplementation(async () => {
      if (Date.now() - serverActivityAt >= 30 * 60_000) {
        return new Response(null, { status: 401 });
      }
      serverActivityAt = Date.now();
      return new Response(JSON.stringify({ access_token: renewedToken }));
    });

    await markSessionActivity();
    await vi.advanceTimersByTimeAsync(59_000);
    await markSessionActivity();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(vi.getTimerCount()).toBe(0);

    await vi.advanceTimersByTimeAsync(29 * 60_000 + 30_000);
    await expect(markSessionActivity()).resolves.toBe(renewedToken);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('does not schedule recurring activity on an untouched page', async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ access_token: renewedToken }))
    );

    await markSessionActivity();
    await vi.advanceTimersByTimeAsync(2 * 60 * 60_000);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('drops pending activity for a changed session and resets its throttle', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      async () => new Response(JSON.stringify({ access_token: state.token }))
    );
    await markSessionActivity();
    await vi.advanceTimersByTimeAsync(59_000);
    await markSessionActivity();
    state.token = accessToken('cook-b', 'session-b');

    await vi.advanceTimersByTimeAsync(1_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await markSessionActivity();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(1_000);
    await markSessionActivity();
    cancelSessionActivity();
    expect(vi.getTimerCount()).toBe(0);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
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
        json: async () => ({ access_token: renewedToken }),
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
    expect(setToken).toHaveBeenCalledWith(renewedToken);
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
          json: async () => ({ access_token: renewedToken }),
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

  it.each(['client', 'fetch'])(
    'does not replay a delayed %s write after another account signs in',
    async (transport) => {
      let finish!: (response: Response) => void;
      fetchMock.mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            finish = resolve;
          })
      );
      const pending =
        transport === 'client'
          ? apiClient.request('/api/v1/recipes', {
              method: 'POST',
              body: '{"title":"A"}',
            })
          : authenticatedFetch('/api/v1/recipes', {
              method: 'POST',
              body: '{"title":"A"}',
            });
      await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
      state.token = accessToken('cook-b', 'session-b');
      finish(
        new Response(
          JSON.stringify({ detail: 'Could not validate credentials' }),
          { status: 401 }
        )
      );

      if (transport === 'client') {
        await expect(pending).rejects.toThrow();
      } else {
        expect(((await pending) as Response).status).toBe(401);
      }
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(setToken).not.toHaveBeenCalled();
      expect(logout).not.toHaveBeenCalled();
    }
  );

  it.each([
    ['cook-b', 'session-b'],
    ['cook-a', 'session-b'],
    ['cook-b', 'session-a'],
  ])(
    'rejects renewal for mismatched subject/session %s %s',
    async (subject, session) => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ access_token: accessToken(subject, session) })
        )
      );

      await expect(refreshAccessToken(false)).resolves.toBeNull();

      expect(setToken).not.toHaveBeenCalled();
      expect(logout).toHaveBeenCalledWith('expired');
    }
  );

  it('does not install a pending renewal after the local session changes', async () => {
    let finish!: (response: Response) => void;
    fetchMock.mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve;
        })
    );
    const pending = refreshAccessToken(false);
    state.token = accessToken('cook-b', 'session-b');
    finish(new Response(JSON.stringify({ access_token: renewedToken })));

    await expect(pending).resolves.toBeNull();
    expect(setToken).not.toHaveBeenCalled();
    expect(logout).not.toHaveBeenCalled();
  });
});
