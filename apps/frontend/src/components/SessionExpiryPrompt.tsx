import { useEffect, useState } from 'react';
import { refreshAccessToken, revokeSession } from '../api/session';
import { useAuthStore } from '../stores/useAuthStore';
import {
  getSessionClaims,
  getSessionIdentity,
  isSameSession,
} from '../utils/authSession';
import { Button } from './ui/Button';
import { Dialog } from './ui/Dialog';

const WARNING_SECONDS = 5 * 60;

/** Warn before the server's consent deadline; input and timer ticks never extend it. */
export function SessionExpiryPrompt() {
  const token = useAuthStore((state) => state.token);
  const claims = getSessionClaims(token);
  const deadline = claims?.session_exp;
  const [now, setNow] = useState(() => Date.now());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dismissedWarning, setDismissedWarning] = useState<string>();
  const warningKey = `${getSessionIdentity(token)}:${deadline}`;
  const remaining = deadline === undefined ? Infinity : deadline - now / 1000;
  const expired = remaining <= 0;
  const atAbsoluteLimit = deadline === claims?.absolute_exp;

  useEffect(() => {
    if (!token) return;
    const updateClock = () => setNow(Date.now());
    const timer = setInterval(updateClock, 1000);
    window.addEventListener('focus', updateClock);
    document.addEventListener('visibilitychange', updateClock);
    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', updateClock);
      document.removeEventListener('visibilitychange', updateClock);
    };
  }, [token]);

  useEffect(() => {
    if (!token || (deadline !== undefined && !expired)) return;
    // A missing deadline can be an older token; a stale deadline can be a missed tab update.
    void refreshAccessToken(false).then((renewed) => {
      if (!isSameSession(token, useAuthStore.getState().token)) return;
      const currentDeadline = getSessionClaims(
        useAuthStore.getState().token
      )?.session_exp;
      if (currentDeadline && currentDeadline > Date.now() / 1000) return;
      if (!renewed || expired) {
        const serverDeadline = getSessionClaims(renewed)?.session_exp;
        if (!serverDeadline || serverDeadline <= Date.now() / 1000) {
          useAuthStore.getState().logout('expired');
        }
      }
    });
  }, [token, deadline, expired]);

  async function extendSession() {
    setPending(true);
    setError(null);
    const renewed = await refreshAccessToken(true);
    if (isSameSession(token, useAuthStore.getState().token) && !renewed) {
      setError(
        'Unable to extend your session. Check your connection and try again before it expires.'
      );
    }
    setPending(false);
  }

  async function signOut() {
    setPending(true);
    setError(null);
    const revoked = await revokeSession();
    if (isSameSession(token, useAuthStore.getState().token)) {
      if (revoked) {
        useAuthStore.getState().logout('manual');
      } else {
        setError('Unable to sign out. Check your connection and try again.');
      }
    }
    setPending(false);
  }

  return (
    <Dialog
      isOpen={
        Boolean(token) &&
        remaining <= WARNING_SECONDS &&
        !expired &&
        dismissedWarning !== warningKey
      }
      onClose={() => setDismissedWarning(warningKey)}
      size="sm"
      title="Your session expires soon"
      description={
        atAbsoluteLimit
          ? 'You are reaching the 12-hour limit. Sign in again when this session ends.'
          : 'Choose Stay signed in to authorize another hour, up to the 12-hour limit.'
      }
    >
      <p className="text-sm text-gray-700">
        Time remaining: {Math.max(1, Math.ceil(remaining / 60))} minute(s).
        Recoverable form and chat text will be saved in this tab if the session
        expires.
      </p>
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="mt-4 flex justify-end gap-3">
        <Button
          variant="outline"
          onClick={() => setDismissedWarning(warningKey)}
        >
          Not now
        </Button>
        <Button
          variant="outline"
          onClick={() => void signOut()}
          disabled={pending}
        >
          Sign out
        </Button>
        {!atAbsoluteLimit && (
          <Button onClick={() => void extendSession()} disabled={pending}>
            {pending ? 'Please wait...' : 'Stay signed in'}
          </Button>
        )}
      </div>
    </Dialog>
  );
}
