import type { TokenResponse, LoginFormData } from '../../types/auth';
import { apiClient } from '../client';

// Login using OAuth2 form format to match backend
export async function login(form: LoginFormData): Promise<TokenResponse> {
  const formData = new FormData();
  formData.append('username', form.username);
  formData.append('password', form.password);

  return apiClient.request<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      // Override default application/json with form data
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams(formData as any),
  });
}
