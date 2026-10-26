import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { refreshAccessToken, revokeSession } from '../../api/session';
import { useAuthStore } from '../../stores/useAuthStore';
import { SessionExpiryPrompt } from '../SessionExpiryPrompt';
import { mockResizeObserver } from 'jsdom-testing-mocks';

mockResizeObserver();

vi.mock('../../api/session', () => ({
  refreshAccessToken: vi.fn(),
  revokeSession: vi.fn(),
}));

const start = new Date('2026-10-22T12:00:00Z').getTime();
const deadline = start / 1000 + 3600;
const absolute = start / 1000 + 12 * 3600;

function token(consent = deadline, cap = absolute, session = 'session-a') {
  return `header.${btoa(
    JSON.stringify({
      sub: 'cook-a',
      sid: session,
      session_exp: consent,
      absolute_exp: cap,
    })
  )}.signature`;
}

describe('explicit session confirmation', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(start);
    vi.resetAllMocks();
    useAuthStore.setState({
      token: token(),
      user: { id: 'cook-a', username: 'cook', email: 'cook@example.test' },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    useAuthStore.setState({ token: null, user: null });
  });

  it('warns at 55 minutes, but input, focus, and timers never extend consent', async () => {
    render(<SessionExpiryPrompt />);
    await act(() => vi.advanceTimersByTimeAsync(55 * 60_000 - 1000));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(1000));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'a' });
    fireEvent.input(document);
    fireEvent.wheel(document);
    fireEvent.focus(window);
    expect(refreshAccessToken).not.toHaveBeenCalled();
  });

  it('extends only after confirmation and hides the warning', async () => {
    vi.setSystemTime(start + 55 * 60_000);
    vi.mocked(refreshAccessToken).mockImplementation(async (extend) => {
      expect(extend).toBe(true);
      const next = token(Date.now() / 1000 + 3600);
      useAuthStore.getState().setToken(next);
      return next;
    });
    render(<SessionExpiryPrompt />);
    await act(async () => fireEvent.click(screen.getByText('Stay signed in')));
    await act(() => vi.advanceTimersByTimeAsync(400));
    expect(refreshAccessToken).toHaveBeenCalledExactlyOnceWith(true);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('expires an ignored prompt at the exact hour and captures recoverable input', async () => {
    vi.mocked(refreshAccessToken).mockResolvedValue(null);
    const logout = vi.spyOn(useAuthStore.getState(), 'logout');
    render(<SessionExpiryPrompt />);
    await act(() => vi.advanceTimersByTimeAsync(60 * 60_000));
    expect(refreshAccessToken).toHaveBeenCalledExactlyOnceWith(false);
    expect(logout).toHaveBeenCalledWith('expired');
    expect(useAuthStore.getState().token).toBeNull();
    logout.mockRestore();
  });

  it('rechecks expiry immediately after waking from sleep', async () => {
    vi.mocked(refreshAccessToken).mockResolvedValue(null);
    render(<SessionExpiryPrompt />);
    vi.setSystemTime(start + 61 * 60_000);
    await act(async () => fireEvent.focus(window));
    expect(refreshAccessToken).toHaveBeenCalledExactlyOnceWith(false);
    expect(useAuthStore.getState().token).toBeNull();
  });

  it('uses a server-confirmed other-tab extension instead of expiring stale local state', async () => {
    vi.mocked(refreshAccessToken).mockImplementation(async () => {
      const next = token(Date.now() / 1000 + 3600);
      useAuthStore.getState().setToken(next);
      return next;
    });
    render(<SessionExpiryPrompt />);
    vi.setSystemTime(start + 61 * 60_000);
    await act(async () => fireEvent(document, new Event('visibilitychange')));
    expect(useAuthStore.getState().token).not.toBeNull();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('reports a failed extension without granting time or discarding the draft early', async () => {
    vi.setSystemTime(start + 55 * 60_000);
    vi.mocked(refreshAccessToken).mockResolvedValue(null);
    render(<SessionExpiryPrompt />);
    await act(async () => fireEvent.click(screen.getByText('Stay signed in')));
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to extend');
    expect(useAuthStore.getState().token).toBe(token());
    expect(
      screen.getByRole('button', { name: 'Stay signed in' })
    ).toBeEnabled();
  });

  it('requires a new sign-in at the absolute limit instead of offering extension', () => {
    vi.setSystemTime(absolute * 1000 - 5 * 60_000);
    useAuthStore.setState({ token: token(absolute) });
    render(<SessionExpiryPrompt />);
    expect(screen.getByText(/reaching the 12-hour limit/)).toBeInTheDocument();
    expect(screen.queryByText('Stay signed in')).not.toBeInTheDocument();
    expect(refreshAccessToken).not.toHaveBeenCalled();
  });

  it('signs out only after server revocation succeeds', async () => {
    vi.setSystemTime(start + 55 * 60_000);
    vi.mocked(revokeSession)
      .mockResolvedValueOnce(false)
      .mockResolvedValueOnce(true);
    render(<SessionExpiryPrompt />);
    await act(async () => fireEvent.click(screen.getByText('Sign out')));
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to sign out');
    expect(useAuthStore.getState().token).not.toBeNull();
    await act(async () => fireEvent.click(screen.getByText('Sign out')));
    expect(useAuthStore.getState().token).toBeNull();
  });

  it.each(['Escape', 'Not now'])(
    '%s dismisses the real dialog without refreshing or reopening on ticks',
    async (action) => {
      vi.setSystemTime(start + 55 * 60_000);
      render(<SessionExpiryPrompt />);
      const defer = screen.getByRole('button', { name: 'Not now' });
      await act(async () => {
        if (action === 'Escape') {
          fireEvent.keyDown(defer, { key: 'Escape' });
        } else {
          fireEvent.click(defer);
        }
      });
      await act(() => vi.advanceTimersByTimeAsync(60_000));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(refreshAccessToken).not.toHaveBeenCalled();
      expect(useAuthStore.getState().token).toBe(token());
    }
  );

  it('warns for a different session even when its deadline matches a dismissed warning', async () => {
    vi.setSystemTime(start + 55 * 60_000);
    render(<SessionExpiryPrompt />);
    await act(async () => fireEvent.click(screen.getByText('Not now')));
    await act(() => vi.advanceTimersByTimeAsync(400));
    await act(async () => {
      useAuthStore.getState().setToken(token(deadline, absolute, 'session-b'));
    });
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(refreshAccessToken).not.toHaveBeenCalled();
  });

  it('warns again for a later authorized window in the same session', async () => {
    vi.setSystemTime(start + 55 * 60_000);
    render(<SessionExpiryPrompt />);
    await act(async () => fireEvent.click(screen.getByText('Not now')));
    await act(() => vi.advanceTimersByTimeAsync(400));
    await act(async () => {
      useAuthStore.getState().setToken(token(deadline + 3600));
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(60 * 60_000));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it.each([deadline, absolute])(
    'expires at %s even when its warning was dismissed',
    async (end) => {
      vi.setSystemTime(end * 1000 - 5 * 60_000);
      useAuthStore.setState({ token: token(end) });
      vi.mocked(refreshAccessToken).mockResolvedValue(null);
      const logout = vi.spyOn(useAuthStore.getState(), 'logout');
      render(<SessionExpiryPrompt />);
      await act(async () => fireEvent.click(screen.getByText('Not now')));
      await act(() => vi.advanceTimersByTimeAsync(5 * 60_000));
      expect(refreshAccessToken).toHaveBeenCalledExactlyOnceWith(false);
      expect(logout).toHaveBeenCalledWith('expired');
      expect(useAuthStore.getState().token).toBeNull();
      logout.mockRestore();
    }
  );
});
