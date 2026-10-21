/** Read the session and subject for comparison only; the server verifies JWTs. */
export function getSessionIdentity(token: string | null): string | null {
  if (!token) return null;
  try {
    const payload: unknown = JSON.parse(
      atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))
    );
    if (
      typeof payload === 'object' &&
      payload !== null &&
      'sub' in payload &&
      typeof payload.sub === 'string' &&
      'sid' in payload &&
      typeof payload.sid === 'string'
    ) {
      return JSON.stringify([payload.sub, payload.sid]);
    }
  } catch {
    // Legacy or malformed tokens cannot be renewed as a bounded session.
  }
  return null;
}

/** Allow token rotation, but never treat a new login as the original session. */
export function isSameSession(
  expectedToken: string | null,
  currentToken: string | null
): boolean {
  const identity = getSessionIdentity(expectedToken);
  return identity
    ? identity === getSessionIdentity(currentToken)
    : expectedToken === currentToken;
}
