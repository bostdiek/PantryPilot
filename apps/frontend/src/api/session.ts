import { getApiBaseUrl } from './apiConfig';
import { useAuthStore } from '../stores/useAuthStore';
import {
  getSessionClaims,
  getSessionIdentity,
  isSameSession,
} from '../utils/authSession';
import { logger } from '../lib/logger';

let refreshInFlight:
  | { extendSession: boolean; token: string; promise: Promise<string | null> }
  | undefined;
let pendingExtension:
  { token: string; promise: Promise<string | null> } | undefined;

async function requestAccessToken(
  extendSession: boolean
): Promise<string | null> {
  const expectedToken = useAuthStore.getState().token;
  const claims = getSessionClaims(expectedToken);
  if (!expectedToken || !claims) {
    logger.warn('Session renewal requires a session-bound access token');
    return null;
  }

  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': claims.sid,
      },
      body: JSON.stringify({ extend_session: extendSession }),
    });
    if (!response.ok) {
      logger.warn('Session renewal was rejected', {
        'http.response.status_code': response.status,
      });
      return null;
    }

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

    const currentToken = useAuthStore.getState().token;
    const currentDeadline = getSessionClaims(currentToken)?.session_exp;
    const returnedDeadline = getSessionClaims(accessToken)?.session_exp;
    if (
      currentDeadline &&
      returnedDeadline &&
      currentDeadline > returnedDeadline
    ) {
      return currentToken;
    }
    useAuthStore.getState().setToken(accessToken);
    return accessToken;
  } catch (error) {
    logger.warn('Session renewal failed', error);
    return null;
  }
}

function rotateAccessToken(extendSession: boolean): Promise<string | null> {
  const token = useAuthStore.getState().token;
  if (!token) return Promise.resolve(null);
  if (refreshInFlight && isSameSession(token, refreshInFlight.token)) {
    if (!extendSession || refreshInFlight.extendSession) {
      return refreshInFlight.promise;
    }

    const pendingRefresh = refreshInFlight.promise;
    return pendingRefresh.then(() =>
      isSameSession(token, useAuthStore.getState().token)
        ? rotateAccessToken(true)
        : null
    );
  }

  const promise = requestAccessToken(extendSession).finally(() => {
    if (refreshInFlight?.promise === promise) {
      refreshInFlight = undefined;
    }
  });
  refreshInFlight = { extendSession, token, promise };
  return promise;
}

/** Rotate credentials; true explicitly authorizes an extension and gates requests, even while queued. */
export function refreshAccessToken(
  extendSession: boolean
): Promise<string | null> {
  if (!extendSession) return rotateAccessToken(false);
  const token = useAuthStore.getState().token;
  if (!token) return Promise.resolve(null);
  if (pendingExtension && isSameSession(token, pendingExtension.token)) {
    return pendingExtension.promise;
  }
  const promise = rotateAccessToken(true).finally(() => {
    if (pendingExtension?.promise === promise) pendingExtension = undefined;
  });
  pendingExtension = { token, promise };
  return promise;
}

/** Wait through queued explicit confirmation for the current session; failure resolves to null. */
export function waitForSessionExtension(): Promise<string | null> {
  return pendingExtension &&
    isSameSession(useAuthStore.getState().token, pendingExtension.token)
    ? pendingExtension.promise
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
  await waitForSessionExtension();
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
  const claims = getSessionClaims(useAuthStore.getState().token);
  if (!claims) {
    logger.warn('Session revocation requires a session-bound access token');
    return false;
  }
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'X-Session-ID': claims.sid },
    });
    if (!response.ok) {
      logger.warn('Session revocation was rejected', {
        'http.response.status_code': response.status,
      });
    }
    return response.ok;
  } catch (error) {
    logger.warn('Session revocation failed', error);
    return false;
  }
}
