import { useState, type FC, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { forgotPassword } from '../api/endpoints/auth';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { getUserFriendlyErrorMessage } from '../utils/errorMessages';

const ForgotPasswordPage: FC = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const validateEmail = (email: string): string | undefined => {
    if (!email) return 'Email is required';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) return 'Please enter a valid email address';
    return undefined;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const emailError = validateEmail(email);
    if (emailError) {
      setError(emailError);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await forgotPassword(email);
      setSuccess(true);
    } catch (err) {
      const friendlyMessage = getUserFriendlyErrorMessage(err, {
        action: 'send',
        resource: 'password reset email',
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
          <h1 className="mb-2 text-center text-2xl font-bold">
            Reset Your Password
          </h1>
          <p className="mb-6 text-center text-sm text-gray-600">
            Enter your email address and we&apos;ll send you a link to reset
            your password.
          </p>

          {!success ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Email Address"
                name="email"
                type="email"
                value={email}
                onChange={setEmail}
                placeholder="Enter your email"
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
                {isLoading ? 'Sending...' : 'Send Reset Link'}
              </Button>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="rounded-md bg-green-50 p-4 text-center">
                <p className="font-medium text-green-700">Check your email!</p>
                <p className="mt-1 text-sm text-green-600">
                  If an account exists with that email, you&apos;ll receive a
                  password reset link shortly.
                </p>
              </div>
            </div>
          )}

          <div className="mt-6 text-center">
            <Link
              to="/login"
              className="text-sm font-medium text-blue-600 transition-colors hover:text-blue-500"
            >
              ← Back to Login
            </Link>
          </div>
        </Card>
      </div>
    </Container>
  );
};

export default ForgotPasswordPage;
