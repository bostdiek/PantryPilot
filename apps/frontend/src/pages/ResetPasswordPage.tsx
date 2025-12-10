import { useEffect, useState, type FC, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../api/endpoints/auth';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { getUserFriendlyErrorMessage } from '../utils/errorMessages';

interface ValidationErrors {
  password?: string;
  confirmPassword?: string;
}

const ResetPasswordPage: FC = () => {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>(
    {}
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [countdown, setCountdown] = useState(3);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const token = searchParams.get('token');

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

  const validateField = (
    name: 'password' | 'confirmPassword',
    value: string
  ) => {
    let fieldError: string | undefined;

    if (name === 'password') {
      fieldError = validatePassword(value);
      // Also revalidate confirm password when password changes
      const confirmError = confirmPassword
        ? validateConfirmPassword(confirmPassword, value)
        : undefined;
      setValidationErrors((prev) => ({
        ...prev,
        password: fieldError,
        confirmPassword: confirmError,
      }));
    } else {
      fieldError = validateConfirmPassword(value, password);
      setValidationErrors((prev) => ({ ...prev, confirmPassword: fieldError }));
    }
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    validateField('password', value);
    if (error) setError(null);
  };

  const handleConfirmPasswordChange = (value: string) => {
    setConfirmPassword(value);
    validateField('confirmPassword', value);
    if (error) setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!token) {
      setError('No reset token provided. Please request a new password reset.');
      return;
    }

    // Validate all fields
    const passwordError = validatePassword(password);
    const confirmError = validateConfirmPassword(confirmPassword, password);

    setValidationErrors({
      password: passwordError,
      confirmPassword: confirmError,
    });

    if (passwordError || confirmError) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      const friendlyMessage = getUserFriendlyErrorMessage(err, {
        action: 'reset',
        resource: 'password',
      });
      setError(friendlyMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Countdown and redirect after success
  useEffect(() => {
    if (!success) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          navigate('/login', { replace: true });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [success, navigate]);

  // No token provided
  if (!token) {
    return (
      <Container size="sm">
        <div className="flex min-h-screen flex-col items-center justify-center">
          <Card variant="default" className="w-full max-w-md p-6">
            <h1 className="mb-6 text-center text-2xl font-bold">
              Reset Password
            </h1>
            <div className="space-y-4">
              <div className="rounded-md bg-red-50 p-4 text-center">
                <p className="text-sm text-red-700">
                  No reset token provided. Please request a new password reset.
                </p>
              </div>
              <div className="text-center">
                <Link
                  to="/forgot-password"
                  className="font-medium text-blue-600 transition-colors hover:text-blue-500"
                >
                  Request Password Reset
                </Link>
              </div>
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
          <h1 className="mb-2 text-center text-2xl font-bold">
            Set New Password
          </h1>
          <p className="mb-6 text-center text-sm text-gray-600">
            Enter your new password below.
          </p>

          {!success ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="New Password"
                name="password"
                type="password"
                value={password}
                onChange={handlePasswordChange}
                placeholder="Enter new password (min 12 characters)"
                required
                disabled={isLoading}
                error={validationErrors.password}
              />

              <Input
                label="Confirm Password"
                name="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={handleConfirmPasswordChange}
                placeholder="Confirm new password"
                required
                disabled={isLoading}
                error={validationErrors.confirmPassword}
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
                disabled={
                  isLoading ||
                  !!validationErrors.password ||
                  !!validationErrors.confirmPassword
                }
              >
                {isLoading ? 'Resetting...' : 'Reset Password'}
              </Button>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="rounded-md bg-green-50 p-4 text-center">
                <p className="font-medium text-green-700">
                  Password reset successfully!
                </p>
                <p className="mt-1 text-sm text-green-600">
                  Redirecting to login in {countdown} seconds...
                </p>
              </div>
              <div className="text-center">
                <Link
                  to="/login"
                  className="font-medium text-blue-600 transition-colors hover:text-blue-500"
                >
                  Go to Login Now
                </Link>
              </div>
            </div>
          )}
        </Card>
      </div>
    </Container>
  );
};

export default ResetPasswordPage;
