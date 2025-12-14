import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import LoginPage from './LoginPage';

// Mock the auth store
vi.mock('../stores/useAuthStore', () => ({
  useAuthStore: vi.fn(() => ({
    setToken: vi.fn(),
  })),
}));

// Mock the login API
vi.mock('../api/endpoints/auth', () => ({
  login: vi.fn(),
  resendVerification: vi.fn(),
}));

// Mock React Router hooks
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Import after mocking
import { login, resendVerification } from '../api/endpoints/auth';
import { useAuthStore } from '../stores/useAuthStore';

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    localStorage.clear();
  });

  test('redirects to home page by default after successful login', async () => {
    const mockSetToken = vi.fn();
    vi.mocked(useAuthStore).mockReturnValue({
      setToken: mockSetToken,
    } as any);

    vi.mocked(login).mockResolvedValue({
      access_token: 'test-token',
      token_type: 'bearer',
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    );

    // Fill in the form
    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'testuser' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockSetToken).toHaveBeenCalledWith('test-token');
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  test('redirects to intended page from next query parameter after successful login', async () => {
    const mockSetToken = vi.fn();
    vi.mocked(useAuthStore).mockReturnValue({
      setToken: mockSetToken,
    } as any);

    vi.mocked(login).mockResolvedValue({
      access_token: 'test-token',
      token_type: 'bearer',
    });

    render(
      <MemoryRouter initialEntries={['/login?next=%2Frecipes']}>
        <LoginPage />
      </MemoryRouter>
    );

    // Fill in the form
    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'testuser' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockSetToken).toHaveBeenCalledWith('test-token');
      expect(mockNavigate).toHaveBeenCalledWith('/recipes', { replace: true });
    });
  });

  test('redirects to intended page with complex path from next query parameter', async () => {
    const mockSetToken = vi.fn();
    vi.mocked(useAuthStore).mockReturnValue({
      setToken: mockSetToken,
    } as any);

    vi.mocked(login).mockResolvedValue({
      access_token: 'test-token',
      token_type: 'bearer',
    });

    // Test with encoded URL that includes search params
    const encodedPath = encodeURIComponent('/recipes/123?edit=true');
    render(
      <MemoryRouter initialEntries={[`/login?next=${encodedPath}`]}>
        <LoginPage />
      </MemoryRouter>
    );

    // Fill in the form
    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'testuser' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockSetToken).toHaveBeenCalledWith('test-token');
      expect(mockNavigate).toHaveBeenCalledWith('/recipes/123?edit=true', {
        replace: true,
      });
    });
  });

  test('handles login error correctly', async () => {
    const mockSetToken = vi.fn();
    vi.mocked(useAuthStore).mockReturnValue({
      setToken: mockSetToken,
    } as any);

    vi.mocked(login).mockRejectedValue({
      status: 401,
      message: 'Invalid credentials',
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    );

    // Fill in the form
    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'testuser' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'wrongpassword' },
    });

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/invalid username or password/i)
      ).toBeInTheDocument();
      expect(mockSetToken).not.toHaveBeenCalled();
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  test('shows resend verification UI for unverified users', async () => {
    vi.mocked(login).mockRejectedValue({
      status: 403,
      message:
        'Email not verified. Please check your inbox for the verification link.',
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'testuser' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/your email has not been verified/i)
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /resend verification email/i })
      ).toBeInTheDocument();
    });
  });

  test('prompts for email when username is not an email', async () => {
    vi.mocked(login).mockRejectedValue({
      status: 403,
      message: 'Email not verified',
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'not-an-email-username' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /resend verification email/i })
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole('button', { name: /resend verification email/i })
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    });
  });

  test('persists cooldown to localStorage on resend success', async () => {
    const now = new Date('2025-01-01T00:00:00.000Z').valueOf();
    const dateNowSpy = vi.spyOn(Date, 'now').mockReturnValue(now);

    vi.mocked(login).mockRejectedValue({
      status: 403,
      message: 'Email not verified',
    });
    vi.mocked(resendVerification).mockResolvedValue({
      message: 'ok',
    } as any);

    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /resend verification email/i })
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole('button', { name: /resend verification email/i })
    );

    try {
      await waitFor(() => {
        expect(localStorage.getItem('pantrypilot_resend_cooldown')).toBe(
          (Date.now() + 60000).toString()
        );
        expect(
          screen.getByRole('button', { name: /resend in 60s/i })
        ).toBeInTheDocument();
        expect(
          screen.getByText(/a new verification link has been sent/i)
        ).toBeInTheDocument();
      });
    } finally {
      dateNowSpy.mockRestore();
    }
  });

  test('persists cooldown to localStorage on resend failure', async () => {
    const now = new Date('2025-01-01T00:00:00.000Z').valueOf();
    const dateNowSpy = vi.spyOn(Date, 'now').mockReturnValue(now);

    vi.mocked(login).mockRejectedValue({
      status: 403,
      message: 'Email not verified',
    });
    vi.mocked(resendVerification).mockRejectedValue(new Error('boom'));

    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /resend verification email/i })
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole('button', { name: /resend verification email/i })
    );

    try {
      await waitFor(() => {
        expect(localStorage.getItem('pantrypilot_resend_cooldown')).toBe(
          (Date.now() + 60000).toString()
        );
        expect(
          screen.getByRole('button', { name: /resend in 60s/i })
        ).toBeInTheDocument();
        expect(
          screen.getByText(/a new verification link has been sent/i)
        ).toBeInTheDocument();
      });
    } finally {
      dateNowSpy.mockRestore();
    }
  });

  test('initializes cooldown from localStorage on mount', async () => {
    const now = new Date('2025-01-01T00:00:00.000Z').valueOf();
    const dateNowSpy = vi.spyOn(Date, 'now').mockReturnValue(now);

    localStorage.setItem(
      'pantrypilot_resend_cooldown',
      (Date.now() + 60000).toString()
    );

    vi.mocked(login).mockRejectedValue({
      status: 403,
      message: 'Email not verified',
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    try {
      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /resend in 60s/i })
        ).toBeInTheDocument();
      });
    } finally {
      dateNowSpy.mockRestore();
    }
  });
});
