import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { server } from '../../test/mocks/server';
import ForgotPasswordPage from '../ForgotPasswordPage';

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderPage = () =>
    render(
      <MemoryRouter initialEntries={['/forgot-password']}>
        <ForgotPasswordPage />
      </MemoryRouter>
    );

  it('validates required email', async () => {
    const { container } = renderPage();
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected a form');

    // Clicking the submit button triggers native constraint validation for required/type=email
    // which can prevent our onSubmit handler from firing in jsdom. Submit the form directly.
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeDefined();
    });
  });

  it('validates email format', async () => {
    const user = userEvent.setup();
    const { container } = renderPage();
    const form = container.querySelector('form');
    if (!form) throw new Error('Expected a form');

    await user.type(screen.getByLabelText(/email address/i), 'not-an-email');

    // Bypass native type=email constraint validation so the component's custom validator runs.
    fireEvent.submit(form);

    await waitFor(() => {
      expect(
        screen.getByText(/please enter a valid email address/i)
      ).toBeDefined();
    });
  });

  it('shows success message after submitting', async () => {
    const user = userEvent.setup();
    server.use(
      http.post('*/api/v1/auth/forgot-password', async ({ request }) => {
        const body = (await request.json()) as { email?: string };
        if (!body.email) {
          return HttpResponse.json(
            { error: { type: 'validation_error', message: 'email required' } },
            { status: 422 }
          );
        }
        return HttpResponse.json({ message: 'ok' });
      })
    );

    renderPage();

    await user.type(
      screen.getByLabelText(/email address/i),
      'test@example.com'
    );
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByText(/check your email/i)).toBeDefined();
    });
  });

  it('shows a friendly error message when request fails', async () => {
    const user = userEvent.setup();
    server.use(
      http.post('*/api/v1/auth/forgot-password', () => {
        return HttpResponse.json(
          { error: { type: 'internal_error', message: 'boom' } },
          { status: 500 }
        );
      })
    );

    renderPage();

    await user.type(
      screen.getByLabelText(/email address/i),
      'test@example.com'
    );
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          /something went wrong|unable to connect|request failed/i
        )
      ).toBeDefined();
    });
  });
});
