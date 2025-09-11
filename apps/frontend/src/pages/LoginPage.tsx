import { useState, type FC, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { login } from '../api/endpoints/auth';
import { userProfileApi } from '../api/endpoints/userProfile';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { useAuthStore } from '../stores/useAuthStore';
import type { LoginFormData, AuthUser } from '../types/auth';
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
    if (error) setError(null);
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
        console.error('Failed to fetch user profile after login:', profileErr);
        // Continue with navigation even if profile fetch fails
        // The profile will be fetched later by the UserProfilePage
      }

      // Navigate to intended page or home
      navigate(from, { replace: true });
    } catch (err: any) {
      // Use centralized error message handling
      const friendlyMessage = getUserFriendlyErrorMessage(err, { 
        action: 'login',
        resource: 'user' 
      });
      setError(friendlyMessage);
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

          <div className="mt-6 text-center">
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
