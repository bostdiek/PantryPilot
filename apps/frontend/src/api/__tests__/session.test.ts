import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../../stores/useAuthStore';
import { apiClient } from '../client';
import {
  authenticatedFetch,
  refreshAccessToken,
  revokeSession,
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
    vi.useRealTimers();
  });

  it('silent renewal does not extend consent or schedule network activity', async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ access_token: renewedToken }))
    );

    await refreshAccessToken(false);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      headers: expect.objectContaining({ 'X-Session-ID': 'session-a' }),
      body: JSON.stringify({ extend_session: false }),
    });
    await vi.advanceTimersByTimeAsync(2 * 60 * 60_000);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('explicit renewal and logout select the initiating session cookie', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ access_token: renewedToken }))
    );
    await refreshAccessToken(true);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      headers: expect.objectContaining({ 'X-Session-ID': 'session-a' }),
      body: JSON.stringify({ extend_session: true }),
    });
    await revokeSession();
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      headers: { 'X-Session-ID': 'session-a' },
      credentials: 'include',
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
      body: JSON.stringify({ extend_session: false }),
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

  it.each([401, 403])(
    'ends raw-fetch sessions only on terminal renewal rejection %s',
    async (status) => {
      fetchMock
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({ detail: 'Could not validate credentials' }),
            { status: 401 }
          )
        )
        .mockResolvedValueOnce(new Response('{}', { status }));
      const response = await authenticatedFetch('/api/v1/recipes', {
        method: 'POST',
      });
      expect(response.status).toBe(401);
      expect(logout).toHaveBeenCalledExactlyOnceWith('expired');
      expect(state.token).toBeNull();
      expect(fetchMock).toHaveBeenCalledTimes(2);
    }
  );

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

  it.each(['client', 'fetch'])(
    'gates a %s retry through confirmation queued after its 401',
    async (transport) => {
      const completions: Array<(response: Response) => void> = [];
      let resourceCalls = 0;
      fetchMock.mockImplementation((input) => {
        if (String(input).includes('/api/v1/auth/refresh')) {
          return new Promise<Response>((resolve) => completions.push(resolve));
        }
        resourceCalls += 1;
        return Promise.resolve(
          resourceCalls === 1
            ? new Response(
                JSON.stringify({ detail: 'Could not validate credentials' }),
                { status: 401 }
              )
            : new Response('{"saved":true}')
        );
      });
      const write =
        transport === 'client'
          ? apiClient.request('/api/v1/recipes', { method: 'POST' })
          : authenticatedFetch('/api/v1/recipes', { method: 'POST' });
      await vi.waitFor(() => expect(completions).toHaveLength(1));
      const explicit = refreshAccessToken(true);
      completions[0](
        new Response(JSON.stringify({ access_token: renewedToken }))
      );
      await vi.waitFor(() => expect(completions).toHaveLength(2));
      const callsBeforeConfirmation = resourceCalls;
      const confirmed = accessToken('cook-a', 'session-a', 2);
      completions[1](new Response(JSON.stringify({ access_token: confirmed })));
      await Promise.all([write, explicit]);
      expect(callsBeforeConfirmation).toBe(1);
      expect(resourceCalls).toBe(2);
      expect(fetchMock.mock.calls.at(-1)?.[1].headers).toMatchObject({
        Authorization: `Bearer ${confirmed}`,
      });
    }
  );

  it.each([
    ['client', 'network'],
    ['client', '503'],
    ['fetch', 'network'],
    ['fetch', '503'],
  ])(
    'preserves the session on %s renewal %s failure',
    async (transport, failure) => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ detail: 'Could not validate credentials' }),
          {
            status: 401,
          }
        )
      );
      if (failure === 'network') {
        fetchMock.mockRejectedValueOnce(new TypeError('Offline'));
      } else {
        fetchMock.mockResolvedValueOnce(new Response('{}', { status: 503 }));
      }
      const write =
        transport === 'client'
          ? apiClient.request('/api/v1/recipes', { method: 'POST' })
          : authenticatedFetch('/api/v1/recipes', { method: 'POST' });
      await expect(write).rejects.toThrow();
      expect(state.token).toBe(originalToken);
      expect(logout).not.toHaveBeenCalled();
      expect(fetchMock).toHaveBeenCalledTimes(2);
    }
  );

  it('does not overwrite a newer same-session deadline received from another tab', async () => {
    const withDeadline = (deadline: number) =>
      `header.${btoa(JSON.stringify({ sub: 'cook-a', sid: 'session-a', session_exp: deadline }))}.signature`;
    state.token = withDeadline(100);
    let finish!: (response: Response) => void;
    fetchMock.mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve;
        })
    );
    const pending = refreshAccessToken(false);
    state.token = withDeadline(300);
    finish(new Response(JSON.stringify({ access_token: withDeadline(100) })));

    await expect(pending).resolves.toBe(withDeadline(300));
    expect(setToken).not.toHaveBeenCalled();
  });

  it('serializes explicit confirmation after an in-flight silent refresh', async () => {
    let finish!: (response: Response) => void;
    fetchMock
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            finish = resolve;
          })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: renewedToken }))
      );
    const silent = refreshAccessToken(false);
    const explicit = refreshAccessToken(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    finish(new Response(JSON.stringify({ access_token: renewedToken })));

    await Promise.all([silent, explicit]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(
      fetchMock.mock.calls.map(([, init]) => JSON.parse(init.body))
    ).toEqual([{ extend_session: false }, { extend_session: true }]);
  });

  it.each(['client', 'fetch'])(
    'gates %s writes immediately through queued confirmation and coalesces clicks',
    async (transport) => {
      const completions: Array<(response: Response) => void> = [];
      fetchMock.mockImplementation((input) => {
        if (String(input).includes('/api/v1/auth/refresh')) {
          return new Promise<Response>((resolve) => completions.push(resolve));
        }
        return Promise.resolve(new Response('{"saved":true}'));
      });
      const silent = refreshAccessToken(false);
      const explicit = refreshAccessToken(true);
      expect(refreshAccessToken(true)).toBe(explicit);
      const write =
        transport === 'client'
          ? apiClient.request('/api/v1/recipes', { method: 'POST' })
          : authenticatedFetch('/api/v1/recipes', { method: 'POST' });
      await Promise.resolve();
      expect(fetchMock).toHaveBeenCalledTimes(1);
      completions[0](
        new Response(JSON.stringify({ access_token: renewedToken }))
      );
      await silent;
      await vi.waitFor(() => expect(completions).toHaveLength(2));
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(refreshAccessToken(true)).toBe(explicit);
      completions[1](
        new Response(JSON.stringify({ access_token: renewedToken }))
      );
      await explicit;
      await write;
      expect(fetchMock).toHaveBeenCalledTimes(3);
      expect(fetchMock.mock.calls[2][0]).toContain('/api/v1/recipes');
      expect(fetchMock.mock.calls[2][1].headers).toMatchObject({
        Authorization: `Bearer ${renewedToken}`,
      });
    }
  );

  it.each(['client', 'fetch'])(
    'does not hold the new session %s request behind another session confirmation',
    async (transport) => {
      let finish!: (response: Response) => void;
      fetchMock
        .mockImplementationOnce(
          () =>
            new Promise<Response>((resolve) => {
              finish = resolve;
            })
        )
        .mockResolvedValue(new Response('{"saved":true}'));
      const silent = refreshAccessToken(false);
      const explicit = refreshAccessToken(true);
      state.token = accessToken('cook-b', 'session-b');
      const write =
        transport === 'client'
          ? apiClient.request('/api/v1/recipes', { method: 'POST' })
          : authenticatedFetch('/api/v1/recipes', { method: 'POST' });
      await write;
      expect(fetchMock).toHaveBeenCalledTimes(2);
      finish(new Response(JSON.stringify({ access_token: renewedToken })));
      await Promise.all([silent, explicit]);
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(setToken).not.toHaveBeenCalled();
      expect(logout).not.toHaveBeenCalled();
    }
  );

  it.each(['client', 'fetch'])(
    'releases the %s barrier on failed confirmation and allows a fresh attempt',
    async (transport) => {
      let finish!: (response: Response) => void;
      fetchMock
        .mockImplementationOnce(
          () =>
            new Promise<Response>((resolve) => {
              finish = resolve;
            })
        )
        .mockResolvedValue(new Response('{"saved":true}'));
      const explicit = refreshAccessToken(true);
      const write =
        transport === 'client'
          ? apiClient.request('/api/v1/recipes', { method: 'POST' })
          : authenticatedFetch('/api/v1/recipes', { method: 'POST' });
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const explicitFailure =
        expect(explicit).rejects.toThrow('Unable to renew');
      const writeFailure = expect(write).rejects.toThrow('Unable to renew');
      finish(new Response('{}', { status: 503 }));
      await Promise.all([explicitFailure, writeFailure]);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: renewedToken }))
      );
      await expect(refreshAccessToken(true)).resolves.toBe(renewedToken);
      expect(fetchMock).toHaveBeenCalledTimes(2);
    }
  );
});
