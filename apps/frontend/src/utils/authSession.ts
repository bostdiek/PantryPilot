/** Unverified UI metadata only; authorization and deadlines are enforced by the server. */
export interface SessionClaims {
  sub: string;
  sid: string;
  exp?: number;
  session_exp?: number;
  absolute_exp?: number;
}

/** Read identity and deadline hints without treating JWT decoding as verification. */
export function getSessionClaims(token: string | null): SessionClaims | null {
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
      const numericClaim = (key: string): number | undefined => {
        const value = key in payload ? Reflect.get(payload, key) : undefined;
        return typeof value === 'number' && Number.isFinite(value)
          ? value
          : undefined;
      };
      return {
        sub: payload.sub,
        sid: payload.sid,
        exp: numericClaim('exp'),
        session_exp: numericClaim('session_exp'),
        absolute_exp: numericClaim('absolute_exp'),
      };
    }
  } catch {
    // Legacy or malformed tokens cannot be renewed as a bounded session.
  }
  return null;
}

/** Compare identity only, allowing access-token rotation within a session. */
export function getSessionIdentity(token: string | null): string | null {
  const claims = getSessionClaims(token);
  return claims ? JSON.stringify([claims.sub, claims.sid]) : null;
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
