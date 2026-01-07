import { useEffect, useState, type FC } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { useResendCooldown } from '../hooks/useResendCooldown';
import { validateEmail as validateEmailUtil } from '../utils/emailValidation';
import { handleResendVerification } from '../utils/resendVerification';

const ResendVerificationPage: FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();

  // Get email from navigation state (preferred) or URL params
  // URL params are immediately cleared to prevent leakage
  const emailFromParams = searchParams.get('email') || '';
  const emailFromState = (location.state as { email?: string })?.email || '';
  const initialEmail = emailFromState || emailFromParams;

  const [email, setEmail] = useState(initialEmail);
  const [emailError, setEmailError] = useState('');
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);

  const { cooldown, startCooldown } = useResendCooldown();

  // Clear email from URL query params after mounting to prevent leakage
  useEffect(() => {
    if (searchParams.has('email')) {
      // Replace URL without email param to prevent exposure in logs/referrer
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const validateEmail = (emailToValidate: string): boolean => {
    const error = validateEmailUtil(emailToValidate);
    setEmailError(error);
    return error === '';
  };

  const handleResend = async () => {
    if (!validateEmail(email)) {
      return;
    }

    setResendLoading(true);
    setResendSuccess(false);

    await handleResendVerification(email);

    setResendSuccess(true);
    startCooldown(60);
    setResendLoading(false);
  };

  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (emailError) {
      setEmailError('');
    }
    if (resendSuccess) {
      setResendSuccess(false);
    }
  };

  return (
    <Container size="sm">
      <div className="flex min-h-screen flex-col items-center justify-center">
        <Card variant="default" className="w-full max-w-md p-6">
          <div className="text-center">
            {/* Icon */}
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
              <svg
                className="h-6 w-6 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
            </div>

            <h1 className="mb-2 text-2xl font-bold text-gray-900">
              Verify Your Email
            </h1>
            <p className="mb-6 text-gray-600">
              Enter your email address to receive a new verification link.
            </p>
          </div>

          {/* Email Input Form */}
          <div className="space-y-4">
            <Input
              label="Email Address"
              type="email"
              value={email}
              onChange={handleEmailChange}
              placeholder="Enter your email address"
              required
              disabled={resendLoading}
              error={emailError}
              autoComplete="email"
            />

            <Button
              type="button"
              variant="primary"
              className="w-full"
              onClick={handleResend}
              disabled={cooldown > 0 || resendLoading || !email}
              loading={resendLoading}
            >
              {cooldown > 0
                ? `Resend in ${cooldown}s`
                : 'Send Verification Email'}
            </Button>

            {resendSuccess && (
              <div className="rounded-md bg-green-50 p-4">
                <p className="text-sm font-medium text-green-700">
                  Verification email sent!
                </p>
                <p className="mt-1 text-sm text-green-600">
                  If an unverified account exists with that email, a new
                  verification link has been sent. Please check your inbox.
                </p>
              </div>
            )}

            <div className="pt-4 text-center text-sm text-gray-600">
              <p>
                Already verified?{' '}
                <Link
                  to="/login"
                  className="font-medium text-blue-600 transition-colors hover:text-blue-500"
                >
                  Go to Login
                </Link>
              </p>
              <p className="mt-2">
                Don&apos;t have an account?{' '}
                <Link
                  to="/register"
                  className="font-medium text-blue-600 transition-colors hover:text-blue-500"
                >
                  Register
                </Link>
              </p>
            </div>
          </div>
        </Card>
      </div>
    </Container>
  );
};

export default ResendVerificationPage;
