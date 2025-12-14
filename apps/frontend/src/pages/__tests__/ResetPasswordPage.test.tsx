import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { server } from '../../test/mocks/server';
import ResetPasswordPage from '../ResetPasswordPage';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  } as any;
});

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  const renderPage = (initialEntries: string[]) =>
    render(
      <MemoryRouter initialEntries={initialEntries}>
        <ResetPasswordPage />
      </MemoryRouter>
    );

  it('shows an error when token is missing', () => {
    renderPage(['/reset-password']);

    expect(screen.getByText(/no reset token provided/i)).toBeDefined();
    expect(
      screen.getByRole('link', { name: /request password reset/i })
    ).toBeDefined();
  });

  it('validates password and confirmation', async () => {
    const user = userEvent.setup();
    renderPage(['/reset-password?token=tok']);

    await user.type(screen.getByLabelText(/new password/i), 'short');
    await user.type(screen.getByLabelText(/confirm password/i), 'different');

    await user.click(screen.getByRole('button', { name: /reset password/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/password must be at least 12 characters/i)
      ).toBeDefined();
      expect(screen.getByText(/passwords do not match/i)).toBeDefined();
    });
  });

  it('resets password successfully and redirects after countdown', async () => {
    let intervalCallback: (() => void) | null = null;
    const realSetInterval = globalThis.setInterval;
    const realClearInterval = globalThis.clearInterval;

    vi.spyOn(globalThis, 'setInterval').mockImplementation(((
      cb: any,
      ms: any,
      ...args: unknown[]
    ) => {
      // Only hijack the page's 1s countdown interval.
      if (ms === 1000) {
        intervalCallback = cb as unknown as () => void;
        return 1 as unknown as number;
      }

      return realSetInterval(cb, ms as number, ...(args as []));
    }) as unknown as typeof globalThis.setInterval);

    vi.spyOn(globalThis, 'clearInterval').mockImplementation(((id: number) => {
      if (id === 1) return;
      return realClearInterval(id);
    }) as unknown as typeof globalThis.clearInterval);

    const user = userEvent.setup();

    server.use(
      http.post('*/api/v1/auth/reset-password', () => {
        return HttpResponse.json({ message: 'ok' });
      })
    );

    renderPage(['/reset-password?token=tok']);

    await user.type(screen.getByLabelText(/new password/i), 'password123456');
    await user.type(
      screen.getByLabelText(/confirm password/i),
      'password123456'
    );

    await user.click(screen.getByRole('button', { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByText(/password reset successfully/i)).toBeDefined();
    });

    expect(intervalCallback).not.toBeNull();
    await act(async () => {
      intervalCallback?.();
      intervalCallback?.();
      intervalCallback?.();
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
    });
  });

  it('shows a friendly error message when reset fails', async () => {
    const user = userEvent.setup();
    server.use(
      http.post('*/api/v1/auth/reset-password', () => {
        return HttpResponse.json(
          { error: { type: 'internal_error', message: 'boom' } },
          { status: 500 }
        );
      })
    );

    renderPage(['/reset-password?token=tok']);

    await user.type(screen.getByLabelText(/new password/i), 'password123456');
    await user.type(
      screen.getByLabelText(/confirm password/i),
      'password123456'
    );

    await user.click(screen.getByRole('button', { name: /reset password/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          /something went wrong|request failed|unable to connect/i
        )
      ).toBeDefined();
    });
  });
});
