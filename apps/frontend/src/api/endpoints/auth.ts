import type {
  ForgotPasswordResponse,
  LoginFormData,
  RegisterFormData,
  RegisterResponse,
  ResendVerificationResponse,
  ResetPasswordResponse,
  TokenResponse,
  VerifyEmailResponse,
} from '../../types/auth';
import { apiClient } from '../client';

// Login using OAuth2 form format to match backend
export async function login(form: LoginFormData): Promise<TokenResponse> {
  const entries: [string, string][] = [
    ['username', form.username],
    ['password', form.password],
  ];

  return apiClient.request<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      // Override default application/json with form data
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams(entries),
  });
}

// Register using JSON format to match backend
export async function register(
  data: RegisterFormData
): Promise<RegisterResponse> {
  // Transform RegisterFormData to match backend schema (exclude confirmPassword)
  const { confirmPassword, ...registerData } = data;

  return apiClient.request<RegisterResponse>('/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(registerData),
  });
}

// Verify email with token from URL
export async function verifyEmail(token: string): Promise<VerifyEmailResponse> {
  return apiClient.request<VerifyEmailResponse>('/api/v1/auth/verify-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
}

// Request password reset email
export async function forgotPassword(
  email: string
): Promise<ForgotPasswordResponse> {
  return apiClient.request<ForgotPasswordResponse>(
    '/api/v1/auth/forgot-password',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    }
  );
}

// Reset password with token
export async function resetPassword(
  token: string,
  newPassword: string
): Promise<ResetPasswordResponse> {
  return apiClient.request<ResetPasswordResponse>(
    '/api/v1/auth/reset-password',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    }
  );
}

// Resend verification email
export async function resendVerification(
  email: string
): Promise<ResendVerificationResponse> {
  return apiClient.request<ResendVerificationResponse>(
    '/api/v1/auth/resend-verification',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    }
  );
}
