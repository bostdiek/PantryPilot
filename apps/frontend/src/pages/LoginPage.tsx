import { useState, type FC, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { login } from '../api/endpoints/auth';
import { userProfileApi } from '../api/endpoints/userProfile';
import logoSvg from '../assets/logo/smartmealplanner-logo.svg';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { logger } from '../lib/logger';
import { useAuthStore } from '../stores/useAuthStore';
import type { AuthUser, LoginFormData } from '../types/auth';
import { getUserFriendlyErrorMessage } from '../utils/errorMessages';

const LoginPage: FC = () => {
  const [formData, setFormData] = useState<LoginFormData>({
    username: '',
    password: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const authStore = useAuthStore();

  // Get the intended destination from query parameter or default to home
  const from = searchParams.get('next') || '/';

  const handleInputChange = (name: string) => (value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (error) {
      setError(null);
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
        // Redirect to dedicated resend verification page
        // Use the username (which could be email or username) to populate the email field
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const email = emailRegex.test(formData.username)
          ? formData.username
          : '';

        // Only use navigation state to pass email (not URL params) for security
        navigate('/resend-verification', {
          replace: true,
          state: { email },
        });
        return;
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
        {/* Logo at the top */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <img src={logoSvg} alt="Smart Meal Planner" className="h-20 w-20" />
          <h1 className="text-2xl font-bold text-gray-800">
            Smart Meal Planner
          </h1>
          <p className="text-center text-sm text-gray-600">
            Meet Nibble — your chat assistant for meal planning and groceries.
          </p>
        </div>

        <Card variant="default" className="w-full max-w-md p-6">
          <h1 className="mb-6 text-center text-2xl font-bold">
            Login to Smart Meal Planner
          </h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              name="username"
              type="text"
              value={formData.username}
              onChange={handleInputChange('username')}
              placeholder="Enter your username"
              autoComplete="username"
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
              autoComplete="current-password"
              required
              disabled={isLoading}
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

        {/* AI Recipe Extraction - Key Differentiator */}
        <Card
          variant="default"
          className="mt-6 w-full max-w-md border-2 border-blue-200 bg-blue-50 p-6"
        >
          <div className="mb-4 flex items-center gap-2">
            <span className="text-2xl">✨</span>
            <h2 className="text-lg font-bold text-blue-900">
              AI-Powered Recipe Addition
            </h2>
          </div>
          <p className="mb-4 text-sm text-blue-700">
            Add recipes from anywhere in seconds. Our AI extracts recipe details
            from photos or recipe websites automatically.
          </p>
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <div className="mt-0.5 text-blue-600">📱</div>
              <div>
                <p className="text-sm font-medium text-gray-700">
                  <strong>Snap a Photo</strong> of a recipe from a cookbook or
                  magazine
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="mt-0.5 text-blue-600">🔗</div>
              <div>
                <p className="text-sm font-medium text-gray-700">
                  <strong>Paste a URL</strong> from any recipe website
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="mt-0.5 text-blue-600">⚡</div>
              <div>
                <p className="text-sm font-medium text-gray-700">
                  <strong>AI Extracts</strong> ingredients, instructions &
                  details
                </p>
              </div>
            </div>
          </div>
        </Card>

        {/* Additional Features */}
        <Card variant="default" className="mt-4 w-full max-w-md p-6">
          <h2 className="mb-3 text-base font-semibold text-gray-800">
            Plus All These Features
          </h2>
          <div className="space-y-2">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 text-lg">📅</div>
              <div>
                <h3 className="font-medium text-gray-700">
                  Smart Meal Planning
                </h3>
                <p className="text-xs text-gray-500">
                  Organize weekly meal plans with ease
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="mt-0.5 text-lg">🛒</div>
              <div>
                <h3 className="font-medium text-gray-700">
                  Auto-Generated Grocery Lists
                </h3>
                <p className="text-xs text-gray-500">
                  Shopping lists created from your meal plans
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="mt-0.5 text-lg">📚</div>
              <div>
                <h3 className="font-medium text-gray-700">
                  Recipe Organization
                </h3>
                <p className="text-xs text-gray-500">
                  Categorize and tag all your favorite recipes
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </Container>
  );
};

export default LoginPage;
