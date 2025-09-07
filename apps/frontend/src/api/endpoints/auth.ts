import type {
  LoginFormData,
  RegisterFormData,
  TokenResponse,
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
export async function register(data: RegisterFormData): Promise<TokenResponse> {
  // Transform RegisterFormData to match backend schema (exclude confirmPassword)
  const { confirmPassword, ...registerData } = data;

  return apiClient.request<TokenResponse>('/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(registerData),
  });
}
