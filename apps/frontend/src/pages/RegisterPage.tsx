import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { register } from '../api/endpoints/auth';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { useResendCooldown } from '../hooks/useResendCooldown';
import type { RegisterFormData } from '../types/auth';
import { validateEmail as validateEmailUtil } from '../utils/emailValidation';
import { getUserFriendlyErrorMessage } from '../utils/errorMessages';
import { handleResendVerification } from '../utils/resendVerification';

interface ValidationErrors {
  username?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  first_name?: string;
  last_name?: string;
}

const RegisterPage: React.FC = () => {
  const [formData, setFormData] = useState<RegisterFormData>({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
  });
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>(
    {}
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');

  // Resend verification state
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);

  const { cooldown, startCooldown } = useResendCooldown();

  // Handler for resending verification email
  const handleResend = async () => {
    setResendLoading(true);
    setResendSuccess(false);

    await handleResendVerification(registeredEmail);

    setResendSuccess(true);
    startCooldown(60);
    setResendLoading(false);
  };

  // Validation functions
  const validateUsername = (username: string): string | undefined => {
    if (!username) return 'Username is required';
    if (username.length < 3) return 'Username must be at least 3 characters';
    if (username.length > 32)
      return 'Username must be no more than 32 characters';
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
      return 'Username can only contain letters, numbers, underscores, and hyphens';
    }
    return undefined;
  };

  const validateEmail = (email: string): string | undefined => {
    const error = validateEmailUtil(email);
    return error || undefined;
  };

  const validatePassword = (password: string): string | undefined => {
    if (!password) return 'Password is required';
    if (password.length < 12) return 'Password must be at least 12 characters';
    return undefined;
  };

  const validateConfirmPassword = (
    confirmPassword: string,
    password: string
  ): string | undefined => {
    if (!confirmPassword) return 'Please confirm your password';
    if (confirmPassword !== password) return 'Passwords do not match';
    return undefined;
  };

  const validateFirstName = (firstName: string): string | undefined => {
    if (firstName && firstName.length > 50)
      return 'First name must be no more than 50 characters';
    return undefined;
  };

  const validateLastName = (lastName: string): string | undefined => {
    if (lastName && lastName.length > 50)
      return 'Last name must be no more than 50 characters';
    return undefined;
  };

  // Real-time validation
  const validateField = (name: keyof RegisterFormData, value: string) => {
    let fieldError: string | undefined;

    switch (name) {
      case 'username':
        fieldError = validateUsername(value);
        break;
      case 'email':
        fieldError = validateEmail(value);
        break;
      case 'password':
        fieldError = validatePassword(value);
        // Also revalidate confirm password if it exists
        if (formData.confirmPassword) {
          const confirmError = validateConfirmPassword(
            formData.confirmPassword,
            value
          );
          setValidationErrors((prev) => ({
            ...prev,
            confirmPassword: confirmError,
          }));
        }
        break;
      case 'confirmPassword':
        fieldError = validateConfirmPassword(value, formData.password);
        break;
      case 'first_name':
        fieldError = validateFirstName(value);
        break;
      case 'last_name':
        fieldError = validateLastName(value);
        break;
    }

    setValidationErrors((prev) => ({ ...prev, [name]: fieldError }));
  };

  // Check if form is valid
  const isFormValid = () => {
    const errors = {
      username: validateUsername(formData.username),
      email: validateEmail(formData.email),
      password: validatePassword(formData.password),
      confirmPassword: validateConfirmPassword(
        formData.confirmPassword,
        formData.password
      ),
      first_name: validateFirstName(formData.first_name || ''),
      last_name: validateLastName(formData.last_name || ''),
    };

    return !Object.values(errors).some((error) => error !== undefined);
  };

  const handleInputChange =
    (name: keyof RegisterFormData) => (value: string) => {
      setFormData((prev) => ({ ...prev, [name]: value }));
      // Clear general error when user starts typing
      if (error) setError(null);
      // Perform real-time validation
      validateField(name, value);
    };

  const handleInputBlur = (name: keyof RegisterFormData) => () => {
    // Validate field on blur for immediate feedback
    validateField(name, formData[name] || '');
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Validate all fields before submission
    const errors = {
      username: validateUsername(formData.username),
      email: validateEmail(formData.email),
      password: validatePassword(formData.password),
      confirmPassword: validateConfirmPassword(
        formData.confirmPassword,
        formData.password
      ),
      first_name: validateFirstName(formData.first_name || ''),
      last_name: validateLastName(formData.last_name || ''),
    };

    setValidationErrors(errors);

    // Check if there are any validation errors
    if (Object.values(errors).some((error) => error !== undefined)) {
      setError('Please fix the errors above before submitting');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await register(formData);
      // Show success state - user needs to verify email before logging in
      setRegistrationSuccess(true);
      setRegisteredEmail(response.email);
    } catch (err: unknown) {
      // Use centralized error message handling
      const friendlyMessage = getUserFriendlyErrorMessage(err, {
        action: 'register',
        resource: 'user',
      });
      setError(friendlyMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Show success message after registration
  if (registrationSuccess) {
    return (
      <Container size="sm">
        <div className="flex min-h-screen flex-col items-center justify-center">
          <Card variant="default" className="w-full max-w-md p-6">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <svg
                  className="h-6 w-6 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h1 className="mb-2 text-2xl font-bold text-gray-900">
                Check Your Email
              </h1>
              <p className="mb-6 text-gray-600">
                We sent a verification link to{' '}
                <span className="font-medium">{registeredEmail}</span>
              </p>
              <p className="mb-6 text-sm text-gray-500">
                Click the link in the email to verify your account and start
                using PantryPilot.
              </p>

              {/* Resend verification section */}
              <div className="mb-6 space-y-3">
                <p className="text-sm text-gray-600">
                  Didn&apos;t receive the email?
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleResend}
                  disabled={cooldown > 0 || resendLoading}
                  loading={resendLoading}
                >
                  {cooldown > 0
                    ? `Resend in ${cooldown}s`
                    : 'Resend Verification Email'}
                </Button>
                {resendSuccess && (
                  <p className="text-sm font-medium text-green-600">
                    Verification email sent! Please check your inbox.
                  </p>
                )}
              </div>

              <Link
                to="/login"
                className="inline-block rounded-md bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500"
              >
                Go to Login
              </Link>
            </div>
          </Card>
        </div>
      </Container>
    );
  }

  return (
    <Container size="sm">
      <div className="flex min-h-screen flex-col items-center justify-center">
        <Card variant="default" className="w-full max-w-md p-6">
          <h1 className="mb-6 text-center text-2xl font-bold">
            Join PantryPilot
          </h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              name="username"
              type="text"
              value={formData.username}
              onChange={handleInputChange('username')}
              onBlur={handleInputBlur('username')}
              placeholder="Enter your username"
              required
              disabled={isLoading}
              error={validationErrors.username}
              helperText="3-32 characters, letters, numbers, underscores, and hyphens only"
            />

            <Input
              label="Email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange('email')}
              onBlur={handleInputBlur('email')}
              placeholder="Enter your email address"
              required
              disabled={isLoading}
              error={validationErrors.email}
              autoComplete="email"
            />

            <Input
              label="Password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleInputChange('password')}
              onBlur={handleInputBlur('password')}
              placeholder="Enter your password"
              required
              disabled={isLoading}
              error={validationErrors.password}
              helperText="Minimum 12 characters"
              autoComplete="new-password"
            />

            <Input
              label="Confirm Password"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleInputChange('confirmPassword')}
              onBlur={handleInputBlur('confirmPassword')}
              placeholder="Confirm your password"
              required
              disabled={isLoading}
              error={validationErrors.confirmPassword}
              autoComplete="new-password"
            />

            <Input
              label="First Name"
              name="first_name"
              type="text"
              value={formData.first_name || ''}
              onChange={handleInputChange('first_name')}
              onBlur={handleInputBlur('first_name')}
              placeholder="Enter your first name (optional)"
              disabled={isLoading}
              error={validationErrors.first_name}
              autoComplete="given-name"
            />

            <Input
              label="Last Name"
              name="last_name"
              type="text"
              value={formData.last_name || ''}
              onChange={handleInputChange('last_name')}
              onBlur={handleInputBlur('last_name')}
              placeholder="Enter your last name (optional)"
              disabled={isLoading}
              error={validationErrors.last_name}
              autoComplete="family-name"
            />

            {error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              loading={isLoading}
              disabled={isLoading || !isFormValid()}
            >
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium text-blue-600 transition-colors hover:text-blue-500"
              >
                Login
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </Container>
  );
};

export default RegisterPage;
