import { useEffect, useState, type FC } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { resendVerification } from '../api/endpoints/auth';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { logger } from '../lib/logger';

// LocalStorage key for cooldown persistence
const RESEND_COOLDOWN_KEY = 'pantrypilot_resend_verification_cooldown';

const ResendVerificationPage: FC = () => {
  const [searchParams] = useSearchParams();
  const location = useLocation();

  // Get email from URL params or navigation state
  const emailFromParams = searchParams.get('email') || '';
  const emailFromState = (location.state as { email?: string })?.email || '';
  const initialEmail = emailFromParams || emailFromState;

  const [email, setEmail] = useState(initialEmail);
  const [emailError, setEmailError] = useState('');
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [cooldown, setCooldown] = useState(0);

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

  const validateEmail = (emailToValidate: string): boolean => {
    if (!emailToValidate) {
      setEmailError('Email is required');
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailToValidate)) {
      setEmailError('Please enter a valid email address');
      return false;
    }
    setEmailError('');
    return true;
  };

  const handleResend = async () => {
    if (!validateEmail(email)) {
      return;
    }

    setResendLoading(true);
    setResendSuccess(false);

    try {
      await resendVerification(email);
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
