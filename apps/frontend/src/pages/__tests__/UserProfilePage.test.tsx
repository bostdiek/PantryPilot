import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import UserProfilePage from '../UserProfilePage';

// Mock the stores with simpler setup
const mockUser = {
  id: '123',
  username: 'testuser',
  email: 'test@example.com',
  first_name: 'John',
  last_name: 'Doe',
};

const mockPreferences = {
  familySize: 4,
  defaultServings: 6,
  allergies: ['Peanuts'],
  dietaryRestrictions: ['Vegetarian'],
  theme: 'light' as const,
  units: 'metric' as const,
  mealPlanningDays: 7,
  preferredCuisines: ['Italian'],
};

const mockSetUser = vi.fn();
const mockUpdatePreferences = vi.fn();

vi.mock('../../stores/useAuthStore', () => ({
  useAuthStore: vi.fn(() => ({
    user: mockUser,
    setUser: mockSetUser,
  })),
  useDisplayName: vi.fn(() => 'John Doe'),
}));

vi.mock('../../stores/useUserPreferencesStore', () => ({
  useUserPreferencesStore: vi.fn(() => ({
    preferences: mockPreferences,
    updatePreferences: mockUpdatePreferences,
  })),
}));

describe('UserProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderUserProfilePage = () => {
    return render(
      <MemoryRouter>
        <UserProfilePage />
      </MemoryRouter>
    );
  };

  test('renders profile page with user information', () => {
    renderUserProfilePage();

    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('Manage your account information and preferences')).toBeInTheDocument();
    expect(screen.getByDisplayValue('John')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Doe')).toBeInTheDocument();
    expect(screen.getByDisplayValue('testuser')).toBeInTheDocument();
    expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument();
  });

  test('shows preferences correctly', () => {
    renderUserProfilePage();

    expect(screen.getByDisplayValue('4')).toBeInTheDocument(); // Family size
    expect(screen.getByDisplayValue('6')).toBeInTheDocument(); // Default servings
    expect(screen.getByDisplayValue('7')).toBeInTheDocument(); // Meal planning days
  });

  test('form fields are disabled by default', () => {
    renderUserProfilePage();

    const firstNameInput = screen.getByLabelText('First Name');
    const lastNameInput = screen.getByLabelText('Last Name');
    const usernameInput = screen.getByLabelText(/Username/); // Use regex to handle asterisk
    const emailInput = screen.getByLabelText('Email');

    expect(firstNameInput).toBeDisabled();
    expect(lastNameInput).toBeDisabled();
    expect(usernameInput).toBeDisabled();
    expect(emailInput).toBeDisabled();
  });

  test('email is always disabled with helper text', () => {
    renderUserProfilePage();

    const emailInput = screen.getByLabelText('Email');
    expect(emailInput).toBeDisabled();
    expect(screen.getByText('Email cannot be changed')).toBeInTheDocument();
  });

  test('shows allergies and dietary restrictions', () => {
    renderUserProfilePage();

    expect(screen.getByLabelText('Peanuts')).toBeChecked();
    expect(screen.getByLabelText('Vegetarian')).toBeChecked();
  });

  test('shows preferred cuisines', () => {
    renderUserProfilePage();

    expect(screen.getByLabelText('Italian')).toBeChecked();
  });
});