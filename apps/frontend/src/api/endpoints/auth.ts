import type { ApiResponse } from '../../types/api';
import type { User } from '../../types/User';
import { apiClient } from '../client';

// Login: expects { email, password }, returns token and user info
export async function login(
  email: string,
  password: string
): Promise<ApiResponse<{ token: string; user: User }>> {
  return apiClient.request<ApiResponse<{ token: string; user: User }>>(
    '/api/v1/auth/login',
    {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }
  );
}

// Register: expects { username, email, password }, returns token and user info
export async function register(
  username: string,
  email: string,
  password: string
): Promise<ApiResponse<{ token: string; user: User }>> {
  return apiClient.request<ApiResponse<{ token: string; user: User }>>(
    '/api/v1/auth/register',
    {
      method: 'POST',
      body: JSON.stringify({ username, email, password }),
    }
  );
}

// Logout: typically just invalidates token server-side, may return success/failure
export async function logout(): Promise<ApiResponse<null>> {
  return apiClient.request<ApiResponse<null>>('/api/v1/auth/logout', {
    method: 'POST',
  });
}
