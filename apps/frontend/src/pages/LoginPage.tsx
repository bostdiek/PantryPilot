import { useEffect, useState, type FC, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { login, resendVerification } from '../api/endpoints/auth';
import { userProfileApi } from '../api/endpoints/userProfile';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { logger } from '../lib/logger';
import { useAuthStore } from '../stores/useAuthStore';
import type { AuthUser, LoginFormData } from '../types/auth';
import { getUserFriendlyErrorMessage } from '../utils/errorMessages';

// LocalStorage key for cooldown persistence
const RESEND_COOLDOWN_KEY = 'pantrypilot_resend_cooldown';

const LoginPage: FC = () => {
  const [formData, setFormData] = useState<LoginFormData>({
    username: '',
    password: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Resend verification state
  const [isUnverifiedError, setIsUnverifiedError] = useState(false);
  const [resendEmail, setResendEmail] = useState('');
  const [showEmailInput, setShowEmailInput] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const authStore = useAuthStore();

  // Get the intended destination from query parameter or default to home
  const from = searchParams.get('next') || '/';

  // Initialize cooldown from localStorage on mount
  useEffect(() => {
    const storedCooldown = localStorage.getItem(RESEND_COOLDOWN_KEY);
    if (storedCooldown) {
      const endTime = parseInt(storedCooldown, 10);
      const remaining = Math.ceil((endTime - Date.now()) / 1000);
      if (remaining > 0) {
        setCooldown(remaining);
      } else {
        localStorage.removeItem(RESEND_COOLDOWN_KEY);
      }
    }
  }, []);

  // Cooldown timer effect
  useEffect(() => {
    if (cooldown <= 0) return;

    const timer = setInterval(() => {
      setCooldown((prev) => {
        if (prev <= 1) {
          localStorage.removeItem(RESEND_COOLDOWN_KEY);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [cooldown]);

  const handleInputChange = (name: string) => (value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (error) {
      setError(null);
      setIsUnverifiedError(false);
      setResendSuccess(false);
    }
  };

  const handleResend = async () => {
    // Determine email to use
    const emailToUse = showEmailInput ? resendEmail : formData.username;

    // Check if we need to show email input (username might not be an email)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailToUse)) {
      setShowEmailInput(true);
      return;
    }

    setResendLoading(true);
    try {
      await resendVerification(emailToUse);
      setResendSuccess(true);

      // Set 60 second cooldown
      const endTime = Date.now() + 60000;
      localStorage.setItem(RESEND_COOLDOWN_KEY, endTime.toString());
      setCooldown(60);
    } catch (err) {
      logger.error('Failed to resend verification email:', err);
      // Still show success to prevent enumeration
      setResendSuccess(true);
      // Set 60 second cooldown (still persist to prevent refresh bypass)
      const endTime = Date.now() + 60000;
      localStorage.setItem(RESEND_COOLDOWN_KEY, endTime.toString());
      setCooldown(60);
    } finally {
      setResendLoading(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!formData.username || !formData.password) {
      setError('Please enter both username and password');
      return;
    }

    setIsLoading(true);
    setError(null);
    setIsUnverifiedError(false);
    setResendSuccess(false);

    try {
      const response = await login(formData);

      // Store token using auth store
      authStore.setToken(response.access_token);

      // Fetch user profile after successful authentication
      try {
        const profile = await userProfileApi.getProfile();

        // Convert UserProfileResponse to AuthUser format
        const user: AuthUser = {
          id: profile.id,
          username: profile.username,
          email: profile.email,
          first_name: profile.first_name,
          last_name: profile.last_name,
        };

        // Store user in auth store
        authStore.setUser(user);
      } catch (profileErr) {
        logger.error('Failed to fetch user profile after login:', profileErr);
        // Continue with navigation even if profile fetch fails
        // The profile will be fetched later by the UserProfilePage
      }

      // Navigate to intended page or home
      navigate(from, { replace: true });
    } catch (err: unknown) {
      // Check if this is a 403 "Email not verified" error
      const errorObj = err as { status?: number; message?: string };
      if (
        errorObj.status === 403 &&
        errorObj.message?.toLowerCase().includes('not verified')
      ) {
        setIsUnverifiedError(true);
        setError('Your email has not been verified.');
      } else {
        // Use centralized error message handling
        const friendlyMessage = getUserFriendlyErrorMessage(err, {
          action: 'login',
          resource: 'user',
        });
        setError(friendlyMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container size="sm">
      <div className="flex min-h-screen flex-col items-center justify-center">
        <Card variant="default" className="w-full max-w-md p-6">
          <h1 className="mb-6 text-center text-2xl font-bold">
            Login to PantryPilot
          </h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              name="username"
              type="text"
              value={formData.username}
              onChange={handleInputChange('username')}
              placeholder="Enter your username"
              required
              disabled={isLoading}
            />

            <Input
              label="Password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleInputChange('password')}
              placeholder="Enter your password"
              required
              disabled={isLoading}
            />

            {error && !isUnverifiedError && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {isUnverifiedError && (
              <div className="space-y-3 rounded-md bg-yellow-50 p-4">
                <p className="text-sm font-medium text-yellow-800">
                  Your email has not been verified.
                </p>
                <p className="text-sm text-yellow-700">
                  Please check your inbox for the verification link, or request
                  a new one below.
                </p>

                {!showEmailInput ? (
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
                ) : (
                  <div className="space-y-2">
                    <Input
                      label="Email Address"
                      type="email"
                      value={resendEmail}
                      onChange={setResendEmail}
                      placeholder="Enter your email"
                      disabled={resendLoading}
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={handleResend}
                      disabled={cooldown > 0 || resendLoading || !resendEmail}
                      loading={resendLoading}
                    >
                      {cooldown > 0 ? `Resend in ${cooldown}s` : 'Send'}
                    </Button>
                  </div>
                )}

                {resendSuccess && (
                  <p className="text-sm font-medium text-green-600">
                    If an unverified account exists with that email, a new
                    verification link has been sent.
                  </p>
                )}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              loading={isLoading}
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6 space-y-2 text-center">
            <p className="text-sm text-gray-600">
              <Link
                to="/forgot-password"
                className="font-medium text-blue-600 transition-colors hover:text-blue-500"
              >
                Forgot your password?
              </Link>
            </p>
            <p className="text-sm text-gray-600">
              Need an account?{' '}
              <Link
                to="/register"
                className="font-medium text-blue-600 transition-colors hover:text-blue-500"
              >
                Register
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </Container>
  );
};

export default LoginPage;
