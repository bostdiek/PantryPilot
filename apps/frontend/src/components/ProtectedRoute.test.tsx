import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';

// Mock the auth store
vi.mock('../stores/useAuthStore', () => {
  const baseFns = {
    login: vi.fn(),
    logout: vi.fn(),
    setToken: vi.fn(),
    setUser: vi.fn(),
    getDisplayName: vi.fn(() => 'User'),
  };
  return {
    useAuthStore: vi.fn(() => ({
      hasHydrated: true,
      token: null,
      user: null,
      ...baseFns,
    })),
    useIsAuthenticated: vi.fn(() => false),
  };
});

// Import after mocking
import { useAuthStore, useIsAuthenticated } from '../stores/useAuthStore';

// Mock React Router Navigate to capture redirect behavior
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    Navigate: ({ to }: { to: string }) => {
      mockNavigate(to);
      return <div data-testid="navigate-redirect">{to}</div>;
    },
  };
});

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('shows loading when not hydrated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: false,
      token: null,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
      setToken: vi.fn(),
      setUser: vi.fn(),
      getDisplayName: vi.fn(() => 'User'),
    } as any);
    vi.mocked(useIsAuthenticated).mockReturnValue(false);

    render(
      <MemoryRouter>
        <ProtectedRoute />
      </MemoryRouter>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  test('redirects to login with query parameter when not authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      token: null,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
      setToken: vi.fn(),
      setUser: vi.fn(),
      getDisplayName: vi.fn(() => 'User'),
    } as any);
    vi.mocked(useIsAuthenticated).mockReturnValue(false);

    render(
      <MemoryRouter initialEntries={['/recipes']}>
        <ProtectedRoute />
      </MemoryRouter>
    );

    // Should redirect to login with the current path as query parameter
    expect(mockNavigate).toHaveBeenCalledWith('/login?next=%2Frecipes');
    expect(screen.getByTestId('navigate-redirect')).toHaveTextContent(
      '/login?next=%2Frecipes'
    );
  });

  test('redirects to login with query parameter including search params', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      token: null,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
      setToken: vi.fn(),
      setUser: vi.fn(),
      getDisplayName: vi.fn(() => 'User'),
    } as any);
    vi.mocked(useIsAuthenticated).mockReturnValue(false);

    render(
      <MemoryRouter initialEntries={['/recipes/123?edit=true']}>
        <ProtectedRoute />
      </MemoryRouter>
    );

    // Should preserve both pathname and search params in the redirect
    expect(mockNavigate).toHaveBeenCalledWith(
      '/login?next=%2Frecipes%2F123%3Fedit%3Dtrue'
    );
  });

  test('renders outlet when authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      token: 'valid-token',
      // Provide a user so the effect doesn't attempt a network call + logout
      user: {
        id: '1',
        username: 'tester',
        email: 'tester@example.com',
        first_name: 'Test',
        last_name: 'User',
      },
      login: vi.fn(),
      logout: vi.fn(),
      setToken: vi.fn(),
      setUser: vi.fn(),
      getDisplayName: vi.fn(() => 'Test User'),
    } as any);
    vi.mocked(useIsAuthenticated).mockReturnValue(true);

    render(
      <MemoryRouter>
        <ProtectedRoute />
      </MemoryRouter>
    );

    // Should not redirect when authenticated
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
