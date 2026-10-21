import { getApiBaseUrl } from './apiConfig';
import { useAuthStore } from '../stores/useAuthStore';
import { getSessionIdentity, isSameSession } from '../utils/authSession';
import { logger } from '../lib/logger';

let refreshInFlight:
  | { activity: boolean; token: string; promise: Promise<string | null> }
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
    if (!isSameSession(expectedToken, useAuthStore.getState().token)) {
      return null;
    }
    if (
      !accessToken ||
      !getSessionIdentity(expectedToken) ||
      getSessionIdentity(accessToken) !== getSessionIdentity(expectedToken)
    ) {
      logger.warn('Session renewal returned a different or invalid identity');
      useAuthStore.getState().logout('expired');
      return null;
    }

    useAuthStore.getState().setToken(accessToken);
    return accessToken;
  } catch (error) {
    logger.warn('Session renewal failed', error);
    return null;
  }
}

export function refreshAccessToken(activity: boolean): Promise<string | null> {
  const token = useAuthStore.getState().token;
  if (!token) return Promise.resolve(null);
  if (refreshInFlight && isSameSession(token, refreshInFlight.token)) {
    if (!activity || refreshInFlight.activity) {
      return refreshInFlight.promise;
    }

    const pendingRefresh = refreshInFlight.promise;
    return pendingRefresh.then(() =>
      isSameSession(token, useAuthStore.getState().token)
        ? refreshAccessToken(true)
        : null
    );
  }

  const promise = requestAccessToken(activity).finally(() => {
    if (refreshInFlight?.promise === promise) {
      refreshInFlight = undefined;
    }
  });
  refreshInFlight = { activity, token, promise };
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
  const initiatingToken = useAuthStore.getState().token;
  await waitForSessionActivity();
  if (!isSameSession(initiatingToken, useAuthStore.getState().token)) {
    throw new Error('Session changed before the request could be sent');
  }
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
  if (token) headers[authorizationHeader] = `Bearer ${token}`;

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
  if (!isSameSession(initiatingToken, useAuthStore.getState().token)) {
    return response;
  }

  const renewedToken = await refreshAccessToken(false);
  if (!isSameSession(initiatingToken, useAuthStore.getState().token)) {
    return response;
  }
  if (!renewedToken) {
    if (useAuthStore.getState().token) {
      useAuthStore.getState().logout('expired');
    }
    return response;
  }
  headers[authorizationHeader] = `Bearer ${renewedToken}`;
  const retryResponse = await fetch(input, requestOptions);
  if (
    retryResponse.status === 401 &&
    (await isSessionAuthenticationFailure(retryResponse)) &&
    isSameSession(initiatingToken, useAuthStore.getState().token) &&
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
