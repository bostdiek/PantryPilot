import { useEffect, useState, type FC } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { verifyEmail } from '../api/endpoints/auth';
import { userProfileApi } from '../api/endpoints/userProfile';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { logger } from '../lib/logger';
import { useAuthStore } from '../stores/useAuthStore';
import type { AuthUser } from '../types/auth';
import { getUserFriendlyErrorMessage } from '../utils/errorMessages';

const VerifyEmailPage: FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [countdown, setCountdown] = useState(5);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);
  const setUser = useAuthStore((s) => s.setUser);

  const token = searchParams.get('token');

  useEffect(() => {
    let ignore = false;

    const verifyToken = async () => {
      if (!token) {
        if (!ignore) {
          setError(
            'No verification token provided. Please check your email link.'
          );
          setIsLoading(false);
        }
        return;
      }

      try {
        const response = await verifyEmail(token);

        // Store token in auth store
        setToken(response.access_token);

        // Fetch user profile after successful verification
        try {
          const profile = await userProfileApi.getProfile();
          const user: AuthUser = {
            id: profile.id,
            username: profile.username,
            email: profile.email,
            first_name: profile.first_name,
            last_name: profile.last_name,
          };
          setUser(user);
        } catch (profileErr) {
          logger.error(
            'Failed to fetch user profile after verification:',
            profileErr
          );
          // Continue - user is verified, profile will be fetched later
        }

        if (!ignore) {
          setSuccess(true);
        }
      } catch (err) {
        const friendlyMessage = getUserFriendlyErrorMessage(err, {
          action: 'verify',
          resource: 'email',
        });
        if (!ignore) {
          setError(friendlyMessage);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    void verifyToken();

    return () => {
      ignore = true;
    };
  }, [token, setToken, setUser]);

  // Countdown and redirect after success
  useEffect(() => {
    if (!success) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          navigate('/', { replace: true });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [success, navigate]);

  return (
    <Container size="sm">
      <div className="flex min-h-screen flex-col items-center justify-center">
        <Card variant="default" className="w-full max-w-md p-6">
          <h1 className="mb-6 text-center text-2xl font-bold">
            Email Verification
          </h1>

          {isLoading && (
            <div className="text-center">
              <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
              <p className="text-gray-600">Verifying your email...</p>
            </div>
          )}

          {error && (
            <div className="space-y-4">
              <div className="rounded-md bg-red-50 p-4 text-center">
                <p className="text-sm text-red-700">{error}</p>
              </div>
              <div className="text-center">
                <p className="mb-2 text-sm text-gray-600">
                  Need a new verification link?
                </p>
                <Link
                  to="/login"
                  className="font-medium text-blue-600 transition-colors hover:text-blue-500"
                >
                  Go to Login
                </Link>
              </div>
            </div>
          )}

          {success && (
            <div className="space-y-4">
              <div className="rounded-md bg-green-50 p-4 text-center">
                <p className="font-medium text-green-700">
                  Email verified successfully!
                </p>
                <p className="mt-1 text-sm text-green-600">
                  Redirecting to home in {countdown} seconds...
                </p>
              </div>
              <div className="text-center">
                <Link
                  to="/"
                  className="font-medium text-blue-600 transition-colors hover:text-blue-500"
                >
                  Go to Home Now
                </Link>
              </div>
            </div>
          )}
        </Card>
      </div>
    </Container>
  );
};

export default VerifyEmailPage;
