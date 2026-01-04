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
import { login } from '../api/endpoints/auth';
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

  test('redirects to resend verification page for unverified users with email', async () => {
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
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        '/resend-verification?email=test%40example.com',
        expect.objectContaining({
          replace: true,
          state: { email: 'test@example.com' },
        })
      );
    });
  });

  test('redirects to resend verification page for unverified users without email', async () => {
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
      expect(mockNavigate).toHaveBeenCalledWith(
        '/resend-verification?email=',
        expect.objectContaining({
          replace: true,
          state: { email: '' },
        })
      );
    });
  });
});
