import { beforeEach, describe, expect, test, vi } from 'vitest';

import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navigation from './Navigation';

// Mock the auth store
vi.mock('../stores/useAuthStore', () => {
  return {
    useAuthStore: vi.fn(() => ({
      hasHydrated: true,
      logout: vi.fn(),
      token: null,
      user: null,
    })),
    useIsAuthenticated: vi.fn(() => false),
    useDisplayName: vi.fn(() => 'Guest'),
  };
});

// Import after mocking
import {
  useAuthStore,
  useDisplayName,
  useIsAuthenticated,
} from '../stores/useAuthStore';

describe('Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('shows login button when not authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      logout: vi.fn(),
      token: null,
      user: null,
    } as any);
    vi.mocked(useDisplayName).mockReturnValue('Guest');
    vi.mocked(useIsAuthenticated).mockReturnValue(false);

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    // Should show Login button when not authenticated
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();

    // Should not show navigation links when not authenticated
    expect(
      screen.queryByRole('link', { name: /^home$/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: /^recipes$/i })
    ).not.toBeInTheDocument();
  });

  test('shows navigation links and logout button when authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      logout: vi.fn(),
      token: 'tok',
      user: { id: '1', username: 'tester', email: 't@example.com' },
    } as any);
    vi.mocked(useDisplayName).mockReturnValue('Tester');
    vi.mocked(useIsAuthenticated).mockReturnValue(true);

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    // Should show navigation links when authenticated
    expect(screen.getByRole('link', { name: /^home$/i })).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /^recipes$/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /^assistant$/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /meal plan/i })
    ).toBeInTheDocument();

    // User menu button should be present
    const userMenuButton = screen.getByRole('button', { name: /user menu/i });
    expect(userMenuButton).toBeInTheDocument();

    // Logout not visible before opening menu
    expect(
      screen.queryByRole('button', { name: /logout/i })
    ).not.toBeInTheDocument();

    // Open the user menu
    fireEvent.click(userMenuButton);

    // Should show Logout button when authenticated after opening menu
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
  });

  test('shows nothing when not hydrated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: false,
      logout: vi.fn(),
      token: null,
      user: null,
    } as any);
    vi.mocked(useDisplayName).mockReturnValue('Guest');
    vi.mocked(useIsAuthenticated).mockReturnValue(false);

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    // Should not show any auth buttons when not hydrated
    expect(
      screen.queryByRole('button', { name: /login/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /logout/i })
    ).not.toBeInTheDocument();
  });

  test('renders mobile hamburger toggle button for authenticated users', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      logout: vi.fn(),
      token: 'tok',
      user: { id: '1', username: 'tester', email: 't@example.com' },
    } as any);
    vi.mocked(useDisplayName).mockReturnValue('Tester');
    vi.mocked(useIsAuthenticated).mockReturnValue(true);

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    // Mobile hamburger button should be present for authenticated users
    const toggleButton = screen.getByRole('button', {
      name: /toggle mobile menu/i,
    });
    expect(toggleButton).toBeInTheDocument();
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
  });

  test('expands and collapses mobile menu when toggle button is clicked', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      logout: vi.fn(),
      token: 'tok',
      user: { id: '1', username: 'tester', email: 't@example.com' },
    } as any);
    vi.mocked(useDisplayName).mockReturnValue('Tester');
    vi.mocked(useIsAuthenticated).mockReturnValue(true);

    const { container } = render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    const toggleButton = screen.getByRole('button', {
      name: /toggle mobile menu/i,
    });

    // Initially, aria-expanded should be false
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

    // Count initial links - should be desktop links only
    const initialHomeLinks = screen.getAllByRole('link', { name: /^home$/i });
    const initialLinkCount = initialHomeLinks.length;

    // Click to expand mobile menu
    fireEvent.click(toggleButton);

    // Mobile menu should now be expanded
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');

    // Should now have additional links from mobile menu
    const expandedHomeLinks = screen.getAllByRole('link', { name: /^home$/i });
    expect(expandedHomeLinks.length).toBeGreaterThan(initialLinkCount);

    // Click to collapse mobile menu
    fireEvent.click(toggleButton);

    // Mobile menu should be collapsed
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
  });

  test('closes mobile menu when a mobile nav link is clicked', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      hasHydrated: true,
      logout: vi.fn(),
      token: 'tok',
      user: { id: '1', username: 'tester', email: 't@example.com' },
    } as any);
    vi.mocked(useDisplayName).mockReturnValue('Tester');
    vi.mocked(useIsAuthenticated).mockReturnValue(true);

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>
    );

    const toggleButton = screen.getByRole('button', {
      name: /toggle mobile menu/i,
    });

    // Open mobile menu
    fireEvent.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');

    // Click on a mobile nav link (get all links and find one in the mobile menu)
    const allRecipeLinks = screen.getAllByRole('link', { name: /^recipes$/i });
    // The last link should be the mobile one since mobile menu is rendered last
    const mobileRecipeLink = allRecipeLinks[allRecipeLinks.length - 1];
    fireEvent.click(mobileRecipeLink);

    // Mobile menu should be closed after clicking a link
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
  });
});
