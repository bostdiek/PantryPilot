import { act, render, screen, waitFor } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { logger } from '../../lib/logger';
import { useAuthStore } from '../../stores/useAuthStore';
import { server } from '../../test/mocks/server';
import VerifyEmailPage from '../VerifyEmailPage';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  } as any;
});

vi.mock('../../lib/logger', () => ({
  logger: { error: vi.fn(), warn: vi.fn(), info: vi.fn(), debug: vi.fn() },
}));

describe('VerifyEmailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();

    // Reset auth store between tests (persist middleware uses localStorage)
    localStorage.clear();
    useAuthStore.setState({ token: null, user: null });
  });

  const renderPage = (initialEntries: string[]) => {
    return render(
      <MemoryRouter initialEntries={initialEntries}>
        <VerifyEmailPage />
      </MemoryRouter>
    );
  };

  it('shows an error when token is missing', async () => {
    renderPage(['/verify-email']);

    await waitFor(() => {
      expect(screen.getByText(/no verification token provided/i)).toBeDefined();
    });
  });

  it('verifies email, stores token and user, and redirects after countdown', async () => {
    let intervalCallback: (() => void) | null = null;
    vi.spyOn(globalThis, 'setInterval').mockImplementation(((cb: any) => {
      intervalCallback = cb as unknown as () => void;
      return 1 as unknown as number;
    }) as unknown as typeof globalThis.setInterval);
    vi.spyOn(globalThis, 'clearInterval').mockImplementation(
      (() => undefined) as unknown as typeof globalThis.clearInterval
    );

    server.use(
      http.post('*/api/v1/auth/verify-email', () => {
        return HttpResponse.json({
          message: 'ok',
          access_token: 'token-123',
          token_type: 'bearer',
        });
      }),
      http.get('*/api/v1/users/me', () => {
        return HttpResponse.json({
          id: 'u1',
          username: 'test',
          email: 'test@example.com',
          first_name: 'T',
          last_name: 'E',
        });
      })
    );

    renderPage(['/verify-email?token=abc']);

    await waitFor(() => {
      expect(screen.getByText(/email verified successfully/i)).toBeDefined();
    });

    expect(useAuthStore.getState().token).toBe('token-123');
    expect(useAuthStore.getState().user).toEqual(
      expect.objectContaining({
        id: 'u1',
        username: 'test',
        email: 'test@example.com',
      })
    );

    expect(intervalCallback).not.toBeNull();
    await act(async () => {
      intervalCallback?.();
      intervalCallback?.();
      intervalCallback?.();
      intervalCallback?.();
      intervalCallback?.();
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('still succeeds when fetching user profile fails', async () => {
    server.use(
      http.post('*/api/v1/auth/verify-email', () => {
        return HttpResponse.json({
          message: 'ok',
          access_token: 'token-123',
          token_type: 'bearer',
        });
      }),
      http.get('*/api/v1/users/me', () => {
        return HttpResponse.json(
          { error: { type: 'internal_error', message: 'boom' } },
          { status: 500 }
        );
      })
    );

    renderPage(['/verify-email?token=abc']);

    await waitFor(() => {
      expect(screen.getByText(/email verified successfully/i)).toBeDefined();
    });

    expect(useAuthStore.getState().token).toBe('token-123');
    expect(logger.error).toHaveBeenCalled();
  });
});
