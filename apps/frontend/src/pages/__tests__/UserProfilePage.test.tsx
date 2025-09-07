import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import UserProfilePage from '../UserProfilePage';

// Mock data
const mockUser = {
  id: '123',
  username: 'testuser',
  email: 'test@example.com',
  first_name: 'John',
  last_name: 'Doe',
};

const mockPreferences = {
  family_size: 4,
  default_servings: 6,
  allergies: ['Peanuts'],
  dietary_restrictions: ['Vegetarian'],
  theme: 'light' as const,
  units: 'metric' as const,
  meal_planning_days: 7,
  preferred_cuisines: ['Italian'],
};

// Derived frontend shape used by store
const frontendPrefs = {
  familySize: mockPreferences.family_size,
  defaultServings: mockPreferences.default_servings,
  allergies: mockPreferences.allergies,
  dietaryRestrictions: mockPreferences.dietary_restrictions,
  theme: mockPreferences.theme,
  units: mockPreferences.units,
  mealPlanningDays: mockPreferences.meal_planning_days,
  preferredCuisines: mockPreferences.preferred_cuisines,
};

const mockSetUser = vi.fn();
const mockUpdatePreferences = vi.fn();
const mockSyncWithBackend = vi.fn();

// Mock auth store WITH getState because apiClient calls useAuthStore.getState()
vi.mock('../../stores/useAuthStore', () => {
  return {
    useAuthStore: Object.assign(
      // callable hook returning slice used in component
      (selector?: any) => {
        const state = {
          token: 'tok',
          user: mockUser,
          setUser: mockSetUser,
          login: vi.fn(),
          logout: vi.fn(),
          setToken: vi.fn(),
          getDisplayName: () => 'John Doe',
        } as any;
        return selector ? selector(state) : state;
      },
      {
        // getState used by apiClient
        getState: vi.fn(() => ({ token: 'tok', user: mockUser })),
      }
    ),
    useDisplayName: vi.fn(() => 'John Doe'),
  };
});

// Mock preferences store
vi.mock('../../stores/useUserPreferencesStore', () => ({
  useUserPreferencesStore: (selector?: any) => {
    const state = {
      preferences: frontendPrefs,
      isLoaded: true,
      updatePreferences: mockUpdatePreferences,
      resetPreferences: vi.fn(),
      loadPreferences: vi.fn(),
      syncWithBackend: mockSyncWithBackend,
    };
    return selector ? selector(state) : state;
  },
}));

// Mock userProfileApi so no real fetch occurs & returns backend style
vi.mock('../../api/endpoints/userProfile', () => ({
  userProfileApi: {
    getProfile: vi.fn(async () => ({
      id: mockUser.id,
      username: mockUser.username,
      email: mockUser.email,
      first_name: mockUser.first_name,
      last_name: mockUser.last_name,
      preferences: mockPreferences,
    })),
    updateProfile: vi.fn(),
    updatePreferences: vi.fn(async () => mockPreferences),
  },
}));

async function renderAndWait() {
  render(
    <MemoryRouter>
      <UserProfilePage />
    </MemoryRouter>
  );
  // Wait for spinner to disappear and heading to appear
  await waitFor(() => {
    expect(
      screen.getByRole('heading', { name: 'Profile' })
    ).toBeInTheDocument();
  });
}

describe('UserProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders profile page with user information', async () => {
    await renderAndWait();

    expect(
      screen.getByRole('heading', { name: 'Profile' })
    ).toBeInTheDocument();
    expect(
      screen.getByText('Manage your account information and preferences')
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue('John')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Doe')).toBeInTheDocument();
    expect(screen.getByDisplayValue('testuser')).toBeInTheDocument();
    expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument();
  });

  test('shows preferences correctly', async () => {
    await renderAndWait();

    expect(screen.getByDisplayValue('4')).toBeInTheDocument(); // Family size
    expect(screen.getByDisplayValue('6')).toBeInTheDocument(); // Default servings
    expect(screen.getByDisplayValue('7')).toBeInTheDocument(); // Meal planning days
  });

  test('form fields are disabled by default', async () => {
    await renderAndWait();

    const firstNameInput = screen.getByLabelText('First Name');
    const lastNameInput = screen.getByLabelText('Last Name');
    const usernameInput = screen.getByLabelText(/Username/); // Use regex to handle asterisk
    const emailInput = screen.getByLabelText('Email');

    expect(firstNameInput).toBeDisabled();
    expect(lastNameInput).toBeDisabled();
    expect(usernameInput).toBeDisabled();
    expect(emailInput).toBeDisabled();
  });

  test('email is always disabled with helper text', async () => {
    await renderAndWait();

    const emailInput = screen.getByLabelText('Email');
    expect(emailInput).toBeDisabled();
    expect(screen.getByText('Email cannot be changed')).toBeInTheDocument();
  });

  test('shows allergies and dietary restrictions', async () => {
    await renderAndWait();

    // Using getByLabelText with accessible name (span text) wraps input so label text accessible
    expect(screen.getByLabelText('Peanuts')).toBeChecked();
    expect(screen.getByLabelText('Vegetarian')).toBeChecked();
  });

  test('shows preferred cuisines', async () => {
    await renderAndWait();

    expect(screen.getByLabelText('Italian')).toBeChecked();
  });
});
