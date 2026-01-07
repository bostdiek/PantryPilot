import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import ResendVerificationPage from '../ResendVerificationPage';

// Mock the resendVerification utility
vi.mock('../../utils/resendVerification', () => ({
  handleResendVerification: vi.fn(),
}));

// Import after mocking
import { handleResendVerification } from '../../utils/resendVerification';

describe('ResendVerificationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  test('renders the page correctly', () => {
    render(
      <MemoryRouter initialEntries={['/resend-verification']}>
        <ResendVerificationPage />
      </MemoryRouter>
    );

    expect(
      screen.getByRole('heading', { name: /verify your email/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /send verification email/i })
    ).toBeInTheDocument();
  });

  test('pre-populates email from URL params', () => {
    render(
      <MemoryRouter
        initialEntries={['/resend-verification?email=test@example.com']}
      >
        <ResendVerificationPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(
      /email address/i
    ) as HTMLInputElement;
    expect(emailInput.value).toBe('test@example.com');
  });

  test('button is disabled when email is empty', async () => {
    render(
      <MemoryRouter initialEntries={['/resend-verification']}>
        <ResendVerificationPage />
      </MemoryRouter>
    );

    const button = screen.getByRole('button', {
      name: /send verification email/i,
    });

    expect(button).toBeDisabled();
  });

  test('validates email format', async () => {
    render(
      <MemoryRouter initialEntries={['/resend-verification']}>
        <ResendVerificationPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/email address/i);
    const button = screen.getByRole('button', {
      name: /send verification email/i,
    });

    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(
        screen.getByText(/please enter a valid email address/i)
      ).toBeInTheDocument();
    });
  });

  test('sends verification email successfully', async () => {
    vi.mocked(handleResendVerification).mockResolvedValue();

    render(
      <MemoryRouter initialEntries={['/resend-verification']}>
        <ResendVerificationPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/email address/i);
    const button = screen.getByRole('button', {
      name: /send verification email/i,
    });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(handleResendVerification).toHaveBeenCalledWith('test@example.com');
      expect(screen.getByText(/verification email sent!/i)).toBeInTheDocument();
    });
  });

  test('shows cooldown after sending email', async () => {
    vi.mocked(handleResendVerification).mockResolvedValue();

    render(
      <MemoryRouter initialEntries={['/resend-verification']}>
        <ResendVerificationPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/email address/i);
    const button = screen.getByRole('button', {
      name: /send verification email/i,
    });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /resend in 60s/i })
      ).toBeInTheDocument();
    });
  });

  test('persists cooldown in localStorage', async () => {
    const now = new Date('2025-01-01T00:00:00.000Z').valueOf();
    const dateNowSpy = vi.spyOn(Date, 'now').mockReturnValue(now);

    vi.mocked(handleResendVerification).mockResolvedValue();

    render(
      <MemoryRouter initialEntries={['/resend-verification']}>
        <ResendVerificationPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/email address/i);
    const button = screen.getByRole('button', {
      name: /send verification email/i,
    });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(button);

    try {
      await waitFor(() => {
        expect(
          localStorage.getItem('pantrypilot_resend_verification_cooldown')
        ).toBe((Date.now() + 60000).toString());
      });
    } finally {
      dateNowSpy.mockRestore();
    }
  });

  test('shows success message even on API failure (prevents enumeration)', async () => {
    vi.mocked(handleResendVerification).mockResolvedValue();

    render(
      <MemoryRouter initialEntries={['/resend-verification']}>
        <ResendVerificationPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/email address/i);
    const button = screen.getByRole('button', {
      name: /send verification email/i,
    });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/verification email sent!/i)).toBeInTheDocument();
    });
  });

  test('has links to login and register', () => {
    render(
      <MemoryRouter initialEntries={['/resend-verification']}>
        <ResendVerificationPage />
      </MemoryRouter>
    );

    const loginLink = screen.getByRole('link', { name: /go to login/i });
    const registerLink = screen.getByRole('link', { name: /register/i });

    expect(loginLink).toBeInTheDocument();
    expect(loginLink.getAttribute('href')).toBe('/login');
    expect(registerLink).toBeInTheDocument();
    expect(registerLink.getAttribute('href')).toBe('/register');
  });
});
