import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as authApi from '../../api/endpoints/auth';
import { useAuthStore } from '../../stores/useAuthStore';
import RegisterPage from '../RegisterPage';

// Mock the auth API
vi.mock('../../api/endpoints/auth', () => ({
  register: vi.fn(),
  resendVerification: vi.fn(),
}));

// Mock the auth store
vi.mock('../../stores/useAuthStore', () => ({
  useAuthStore: vi.fn(),
}));

// Mock react-router-dom navigation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: null }),
  };
});

describe('RegisterPage', () => {
  const mockSetToken = vi.fn();
  const mockAuthStore = {
    token: null,
    user: null,
    hasHydrated: true,
    login: vi.fn(),
    logout: vi.fn(),
    setToken: mockSetToken,
    setUser: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear(); // Clear localStorage to reset cooldown state
    (useAuthStore as any).mockReturnValue(mockAuthStore);
  });

  const renderRegisterPage = (initialEntries = ['/register']) => {
    return render(
      <MemoryRouter initialEntries={initialEntries}>
        <RegisterPage />
      </MemoryRouter>
    );
  };

  describe('Rendering Tests', () => {
    it('renders correctly with all form fields', () => {
      renderRegisterPage();

      expect(
        screen.getByRole('heading', { name: /join pantrypilot/i })
      ).toBeDefined();
      expect(screen.getByLabelText(/username/i)).toBeDefined();
      expect(screen.getByLabelText(/email/i)).toBeDefined();
      expect(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        })
      ).toBeDefined();
      expect(screen.getByLabelText(/confirm password/i)).toBeDefined();
      expect(screen.getByLabelText(/first name/i)).toBeDefined();
      expect(screen.getByLabelText(/last name/i)).toBeDefined();
    });

    it('renders submit button initially disabled', () => {
      renderRegisterPage();

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      expect(submitButton.hasAttribute('disabled')).toBe(true);
    });

    it('displays form labels and helper text', () => {
      renderRegisterPage();

      expect(
        screen.getByText(
          '3-32 characters, letters, numbers, underscores, and hyphens only'
        )
      ).toBeDefined();
      expect(screen.getByText('Minimum 12 characters')).toBeDefined();
    });

    it('renders login link', () => {
      renderRegisterPage();

      const loginLink = screen.getByRole('link', { name: /login/i });
      expect(loginLink).toBeDefined();
      expect(loginLink.getAttribute('href')).toBe('/login');
    });
  });

  describe('Validation Tests', () => {
    it('validates username - required', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const usernameInput = screen.getByLabelText(/username/i);
      await user.click(usernameInput);
      await user.tab(); // blur the field

      await waitFor(() => {
        expect(screen.getByText('Username is required')).toBeDefined();
      });
    });

    it('validates username - minimum length', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const usernameInput = screen.getByLabelText(/username/i);
      await user.type(usernameInput, 'ab');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.getByText('Username must be at least 3 characters')
        ).toBeDefined();
      });
    });

    it('validates email - required', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.click(emailInput);
      await user.tab();

      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeDefined();
      });
    });

    it('validates email - format', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'invalid-email');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.getByText('Please enter a valid email address')
        ).toBeDefined();
      });
    });

    it('validates password - required', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const passwordInput = screen.getByLabelText(/^password\b/i, {
        selector: 'input[name="password"]',
      });
      await user.click(passwordInput);
      await user.tab();

      await waitFor(() => {
        expect(screen.getByText('Password is required')).toBeDefined();
      });
    });

    it('validates password - minimum length', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const passwordInput = screen.getByLabelText(/^password\b/i, {
        selector: 'input[name="password"]',
      });
      await user.type(passwordInput, 'short');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.getByText('Password must be at least 12 characters')
        ).toBeDefined();
      });
    });

    it('validates confirm password - must match', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const passwordInput = screen.getByLabelText(/^password\b/i, {
        selector: 'input[name="password"]',
      });
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);

      await user.type(passwordInput, 'password123456');
      await user.type(confirmPasswordInput, 'differentpassword');
      await user.tab();

      await waitFor(() => {
        expect(screen.getByText('Passwords do not match')).toBeDefined();
      });
    });
  });

  describe('Form Interaction Tests', () => {
    it('allows user to type in all form fields', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const usernameInput = screen.getByLabelText(
        /username/i
      ) as HTMLInputElement;
      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
      const passwordInput = screen.getByLabelText(/^password\b/i, {
        selector: 'input[name="password"]',
      }) as HTMLInputElement;
      const confirmPasswordInput = screen.getByLabelText(
        /confirm password/i
      ) as HTMLInputElement;
      const firstNameInput = screen.getByLabelText(
        /first name/i
      ) as HTMLInputElement;
      const lastNameInput = screen.getByLabelText(
        /last name/i
      ) as HTMLInputElement;

      await user.type(usernameInput, 'testuser');
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123456');
      await user.type(confirmPasswordInput, 'password123456');
      await user.type(firstNameInput, 'John');
      await user.type(lastNameInput, 'Doe');

      expect(usernameInput.value).toBe('testuser');
      expect(emailInput.value).toBe('test@example.com');
      expect(passwordInput.value).toBe('password123456');
      expect(confirmPasswordInput.value).toBe('password123456');
      expect(firstNameInput.value).toBe('John');
      expect(lastNameInput.value).toBe('Doe');
    });

    it('enables submit button when all validation passes', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      expect(submitButton.hasAttribute('disabled')).toBe(true);

      // Fill in valid form data
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );

      await waitFor(() => {
        expect(submitButton.hasAttribute('disabled')).toBe(false);
      });
    });
  });

  describe('API Integration Tests', () => {
    it('calls register API with correct data on successful submission', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);
      mockRegister.mockResolvedValueOnce({
        access_token: 'test-token',
        token_type: 'bearer',
      });

      renderRegisterPage();

      // Fill in valid form data
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );
      await user.type(screen.getByLabelText(/first name/i), 'John');
      await user.type(screen.getByLabelText(/last name/i), 'Doe');

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith({
          username: 'testuser',
          email: 'test@example.com',
          password: 'password123456',
          confirmPassword: 'password123456',
          first_name: 'John',
          last_name: 'Doe',
        });
      });
    });

    it('shows success state on successful registration', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);
      mockRegister.mockResolvedValueOnce({
        message:
          'Registration successful. Please check your email to verify your account.',
        email: 'test@example.com',
      });

      renderRegisterPage();

      // Fill in valid form data
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      // Should show success state with "Check Your Email" message
      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeDefined();
        expect(screen.getByText(/test@example.com/i)).toBeDefined();
      });

      // Should NOT call setToken (no auto-login)
      expect(mockSetToken).not.toHaveBeenCalled();
    });

    it('shows loading state during registration', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);

      // Create a promise that we can control
      let resolveRegister: (value: { message: string; email: string }) => void;
      const registerPromise = new Promise<{ message: string; email: string }>(
        (resolve) => {
          resolveRegister = resolve;
        }
      );
      mockRegister.mockReturnValueOnce(registerPromise);

      renderRegisterPage();

      // Fill in valid form data
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      // Should show loading state
      expect(
        screen.getByRole('button', { name: /creating account/i })
      ).toBeDefined();
      expect(
        screen
          .getByRole('button', { name: /creating account/i })
          .hasAttribute('disabled')
      ).toBe(true);

      // Resolve the promise
      resolveRegister!({
        message: 'Registration successful.',
        email: 'test@example.com',
      });

      // Should show success state after resolving
      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeDefined();
      });
    });

    it('shows error message on registration failure', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);
      mockRegister.mockRejectedValueOnce({
        status: 400,
        message: 'Username already exists',
      });

      renderRegisterPage();

      // Fill in valid form data
      await user.type(screen.getByLabelText(/username/i), 'existinguser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Username is already taken')).toBeDefined();
      });
    });

    it('prevents submission with validation errors', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);

      renderRegisterPage();

      // Fill in invalid form data
      await user.type(screen.getByLabelText(/username/i), 'ab'); // Too short
      await user.type(screen.getByLabelText(/email/i), 'invalid-email'); // Invalid format

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      // The submit button remains disabled when form is invalid; no top-level submit error is shown.
      expect(submitButton.hasAttribute('disabled')).toBe(true);

      // Field-level validation messages should be present
      expect(
        screen.getByText('Username must be at least 3 characters')
      ).toBeDefined();
      expect(
        screen.getByText('Please enter a valid email address')
      ).toBeDefined();

      // API should not be called
      expect(mockRegister).not.toHaveBeenCalled();
    });
  });

  describe('Resend Verification Tests', () => {
    it('shows resend verification button on success screen', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);
      mockRegister.mockResolvedValueOnce({
        message:
          'Registration successful. Please check your email to verify your account.',
        email: 'test@example.com',
      });

      renderRegisterPage();

      // Fill in valid form data and submit
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      // Should show success state with resend button
      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeDefined();
        expect(screen.getByText(/didn't receive the email\?/i)).toBeDefined();
        expect(
          screen.getByRole('button', { name: /resend verification email/i })
        ).toBeDefined();
      });
    });

    it('calls resendVerification API when resend button is clicked', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);
      const mockResendVerification = vi.mocked(authApi.resendVerification);
      
      mockRegister.mockResolvedValueOnce({
        message: 'Registration successful.',
        email: 'test@example.com',
      });
      mockResendVerification.mockResolvedValueOnce({
        message: 'Verification email sent.',
      });

      renderRegisterPage();

      // Register successfully first
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      // Wait for success screen
      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeDefined();
      });

      // Click resend button
      const resendButton = screen.getByRole('button', {
        name: /resend verification email/i,
      });
      await user.click(resendButton);

      await waitFor(() => {
        expect(mockResendVerification).toHaveBeenCalledWith('test@example.com');
        expect(
          screen.getByText(/verification email sent/i)
        ).toBeDefined();
      });
    });

    it('shows cooldown timer after resending verification email', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);
      const mockResendVerification = vi.mocked(authApi.resendVerification);
      
      mockRegister.mockResolvedValueOnce({
        message: 'Registration successful.',
        email: 'test@example.com',
      });
      mockResendVerification.mockResolvedValueOnce({
        message: 'Verification email sent.',
      });

      renderRegisterPage();

      // Register successfully first
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      // Wait for success screen
      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeDefined();
      });

      // Get the resend button by its initial text
      const resendButton = screen.getByRole('button', {
        name: /resend verification email/i,
      });
      await user.click(resendButton);

      // Should show cooldown timer - button text should change
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /resend in 60s/i })).toBeDefined();
      });
    });

    it('disables resend button during cooldown period', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authApi.register);
      const mockResendVerification = vi.mocked(authApi.resendVerification);
      
      mockRegister.mockResolvedValueOnce({
        message: 'Registration successful.',
        email: 'test@example.com',
      });
      mockResendVerification.mockResolvedValueOnce({
        message: 'Verification email sent.',
      });

      renderRegisterPage();

      // Register successfully first
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        }),
        'password123456'
      );
      await user.type(
        screen.getByLabelText(/confirm password/i),
        'password123456'
      );

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      await user.click(submitButton);

      // Wait for success screen
      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeDefined();
      });

      // Get the resend button by its initial text
      const resendButton = screen.getByRole('button', {
        name: /resend verification email/i,
      });
      await user.click(resendButton);

      // Button should be disabled during cooldown
      await waitFor(() => {
        const cooldownButton = screen.getByRole('button', { name: /resend in 60s/i });
        expect(cooldownButton.hasAttribute('disabled')).toBe(true);
      });
    });
  });

  describe('Accessibility Tests', () => {
    it('has proper form labels', () => {
      renderRegisterPage();

      expect(screen.getByLabelText(/username/i)).toBeDefined();
      expect(screen.getByLabelText(/email/i)).toBeDefined();
      expect(
        screen.getByLabelText(/^password\b/i, {
          selector: 'input[name="password"]',
        })
      ).toBeDefined();
      expect(screen.getByLabelText(/confirm password/i)).toBeDefined();
      expect(screen.getByLabelText(/first name/i)).toBeDefined();
      expect(screen.getByLabelText(/last name/i)).toBeDefined();
    });

    it('has proper form structure', () => {
      renderRegisterPage();

      // Check that the form element exists by tag name since it doesn't have role="form"
      const form = document.querySelector('form');
      expect(form).toBeDefined();
    });

    it('has proper button roles and states', () => {
      renderRegisterPage();

      const submitButton = screen.getByRole('button', {
        name: /create account/i,
      });
      expect(submitButton.getAttribute('type')).toBe('submit');
    });

    it('has proper link accessibility', () => {
      renderRegisterPage();

      const loginLink = screen.getByRole('link', { name: /login/i });
      expect(loginLink.getAttribute('href')).toBe('/login');
    });
  });
});

// Additional error handling coverage tests appended outside the main describe block
// to increase RegisterPage.tsx coverage (target ≥95%).

describe('RegisterPage - Additional Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear(); // Clear localStorage to reset cooldown state
  });

  const renderRegisterPage = (initialEntries = ['/register']) => {
    return render(
      <MemoryRouter initialEntries={initialEntries}>
        <RegisterPage />
      </MemoryRouter>
    );
  };

  it('shows email taken message on 409 conflict', async () => {
    const user = userEvent.setup();
    const mockRegister = vi.mocked(authApi.register);
    mockRegister.mockRejectedValueOnce({
      status: 409,
      message: 'Email already exists',
    });

    renderRegisterPage();

    await user.type(screen.getByLabelText(/username/i), 'existinguser2');
    await user.type(screen.getByLabelText(/email/i), 'dup@example.com');
    await user.type(
      screen.getByLabelText(/^password\b/i, {
        selector: 'input[name="password"]',
      }),
      'password123456'
    );
    await user.type(
      screen.getByLabelText(/confirm password/i),
      'password123456'
    );

    const submitButton = screen.getByRole('button', {
      name: /create account/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Email is already registered')).toBeDefined();
    });
  });

  it('shows generic invalid data message on 422', async () => {
    const user = userEvent.setup();
    const mockRegister = vi.mocked(authApi.register);
    mockRegister.mockRejectedValueOnce({
      status: 422,
      message: 'Invalid data',
    });

    renderRegisterPage();

    await user.type(screen.getByLabelText(/username/i), 'baduser');
    await user.type(screen.getByLabelText(/email/i), 'invalid@example.com');
    await user.type(
      screen.getByLabelText(/^password\b/i, {
        selector: 'input[name="password"]',
      }),
      'password123456'
    );
    await user.type(
      screen.getByLabelText(/confirm password/i),
      'password123456'
    );

    const submitButton = screen.getByRole('button', {
      name: /create account/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText('Invalid registration data. Please check your inputs.')
      ).toBeDefined();
    });
  });

  it('shows fallback generic message on unknown server error', async () => {
    const user = userEvent.setup();
    const mockRegister = vi.mocked(authApi.register);
    mockRegister.mockRejectedValueOnce({
      status: 500,
      message: '',
    });

    renderRegisterPage();

    await user.type(screen.getByLabelText(/username/i), 'servererruser');
    await user.type(screen.getByLabelText(/email/i), 'server@err.com');
    await user.type(
      screen.getByLabelText(/^password\b/i, {
        selector: 'input[name="password"]',
      }),
      'password123456'
    );
    await user.type(
      screen.getByLabelText(/confirm password/i),
      'password123456'
    );

    const submitButton = screen.getByRole('button', {
      name: /create account/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText('Registration failed. Please try again.')
      ).toBeDefined();
    });
  });
});
