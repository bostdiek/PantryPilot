import { describe, expect, test, vi, beforeEach } from 'vitest';

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navigation from './Navigation';

// Mock the auth store
vi.mock('../stores/useAuthStore', () => ({
  useAuthStore: vi.fn(() => ({
    hasHydrated: true,
    isAuthenticated: false,
    logout: vi.fn(),
  })),
}));

// Import after mocking
import { useAuthStore } from '../stores/useAuthStore';

describe('Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('shows login button when not authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      isAuthenticated: false,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    // Should show Login button when not authenticated
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    
    // Should not show navigation links when not authenticated
    expect(screen.queryByRole('link', { name: /^home$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^recipes$/i })).not.toBeInTheDocument();
  });

  test('shows navigation links and logout button when authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      isAuthenticated: true,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    // Should show navigation links when authenticated
    expect(screen.getByRole('link', { name: /^home$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^recipes$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /add recipe/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /meal plan/i })).toBeInTheDocument();
    
    // Should show Logout button when authenticated
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
  });

  test('shows nothing when not hydrated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: false,
      isAuthenticated: false,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    // Should not show any auth buttons when not hydrated
    expect(screen.queryByRole('button', { name: /login/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument();
  });
});
