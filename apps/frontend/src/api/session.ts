import { getApiBaseUrl } from './apiConfig';
import { useAuthStore } from '../stores/useAuthStore';

let refreshInFlight:
  | { activity: boolean; promise: Promise<string | null> }
  | undefined;
let lastActivityRefreshAt = 0;
const ACTIVITY_REFRESH_INTERVAL_MS = 60_000;

async function requestAccessToken(activity: boolean): Promise<string | null> {
  const expectedToken = useAuthStore.getState().token;
  if (!expectedToken) return null;

  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activity }),
    });
    if (!response.ok) return null;

    const body = (await response.json()) as { access_token?: string };
    const accessToken = body.access_token;
    if (!accessToken || useAuthStore.getState().token !== expectedToken) {
      return null;
    }

    useAuthStore.getState().setToken(accessToken);
    return accessToken;
  } catch {
    return null;
  }
}

export function refreshAccessToken(activity: boolean): Promise<string | null> {
  if (refreshInFlight) {
    if (!activity || refreshInFlight.activity) {
      return refreshInFlight.promise;
    }

    const pendingRefresh = refreshInFlight.promise;
    return pendingRefresh.then(() => refreshAccessToken(true));
  }

  const promise = requestAccessToken(activity).finally(() => {
    if (refreshInFlight?.promise === promise) {
      refreshInFlight = undefined;
    }
  });
  refreshInFlight = { activity, promise };
  return promise;
}

export function markSessionActivity(): Promise<string | null> {
  const now = Date.now();
  if (now - lastActivityRefreshAt < ACTIVITY_REFRESH_INTERVAL_MS) {
    return waitForSessionActivity();
  }
  lastActivityRefreshAt = now;
  return refreshAccessToken(true).then((token) => {
    if (!token && lastActivityRefreshAt === now) {
      lastActivityRefreshAt = 0;
    }
    return token;
  });
}

export function waitForSessionActivity(): Promise<string | null> {
  return refreshInFlight?.activity
    ? refreshInFlight.promise
    : Promise.resolve(null);
}

async function isSessionAuthenticationFailure(
  response: Response
): Promise<boolean> {
  try {
    const body = (await response.clone().json()) as Record<string, unknown>;
    const detail = typeof body.detail === 'string' ? body.detail : '';
    const errorType =
      typeof body.error === 'object' && body.error !== null
        ? (body.error as { type?: string }).type
        : undefined;
    return (
      detail === 'Could not validate credentials' ||
      detail.startsWith('Session expired') ||
      detail.startsWith('Your session ended') ||
      errorType === 'unauthorized' ||
      errorType === 'token_expired'
    );
  } catch {
    return false;
  }
}

export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  await waitForSessionActivity();
  const headers: Record<string, string> = {};
  if (
    init.headers &&
    typeof init.headers === 'object' &&
    !Array.isArray(init.headers) &&
    !(init.headers instanceof Headers)
  ) {
    Object.assign(headers, init.headers);
  } else {
    new Headers(init.headers).forEach((value, key) => {
      headers[key] = value;
    });
  }
  const authorizationHeader =
    Object.keys(headers).find((key) => key.toLowerCase() === 'authorization') ??
    'Authorization';
  const token = useAuthStore.getState().token;
  if (token) headers[authorizationHeader] = `******;

  const requestOptions: RequestInit = {
    ...init,
    credentials: 'include',
    headers,
  };
  const response = await fetch(input, requestOptions);
  if (response.status !== 401) return response;

  const requestUrl = String(input);
  const path = requestUrl.split('?')[0];
  if (path.includes('/api/v1/auth/')) return response;
  const query = requestUrl.split('?')[1] ?? '';
  if (
    path.includes('/api/v1/ai/drafts/') &&
    new URLSearchParams(query).has('token')
  ) {
    return response;
  }

  if (!(await isSessionAuthenticationFailure(response))) return response;

  const renewedToken = await refreshAccessToken(false);
  if (!renewedToken) {
    if (useAuthStore.getState().token) {
      useAuthStore.getState().logout('expired');
    }
    return response;
  }
  headers[authorizationHeader] = `******;
  const retryResponse = await fetch(input, requestOptions);
  if (
    retryResponse.status === 401 &&
    (await isSessionAuthenticationFailure(retryResponse)) &&
    useAuthStore.getState().token
  ) {
    useAuthStore.getState().logout('expired');
  }
  return retryResponse;
}

export async function revokeSession(): Promise<boolean> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
    return response.ok;
  } catch {
    return false;
  }
}
