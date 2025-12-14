import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LoginFormData, RegisterFormData } from '../../types/auth';
import {
  forgotPassword,
  login,
  register,
  resendVerification,
  resetPassword,
  verifyEmail,
} from '../endpoints/auth';

describe('Auth API', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', fetchMock);
  });

  it('handles login success', async () => {
    const mockToken = {
      access_token: 'test-token',
      token_type: 'bearer',
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(JSON.stringify(mockToken)),
    });

    const formData: LoginFormData = {
      username: 'testuser',
      password: 'testpass',
    };

    const result = await login(formData);
    expect(result).toEqual(mockToken);
  });

  it('handles login failure with 401 error from FastAPI', async () => {
    // This simulates what FastAPI actually returns for 401 errors
    const fastApiError = {
      detail: 'Incorrect username or password', // FastAPI uses 'detail', not 'message'
    };

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: vi.fn().mockResolvedValue(JSON.stringify(fastApiError)),
    });

    const formData: LoginFormData = {
      username: 'wronguser',
      password: 'wrongpass',
    };

    await expect(login(formData)).rejects.toMatchObject({
      message: 'Incorrect username or password', // Now it should show the actual FastAPI error
      status: 401,
    });
  });

  it('handles error responses that use message field instead of detail', async () => {
    // Some API responses might use 'message' instead of 'detail'
    const errorWithMessage = {
      message: 'Custom error message',
    };

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: vi.fn().mockResolvedValue(JSON.stringify(errorWithMessage)),
    });

    const formData: LoginFormData = {
      username: 'testuser',
      password: 'testpass',
    };

    await expect(login(formData)).rejects.toMatchObject({
      message: 'Custom error message',
      status: 400,
    });
  });

  it('falls back to generic error when neither detail nor message is present', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: vi.fn().mockResolvedValue(JSON.stringify({})),
    });

    const formData: LoginFormData = {
      username: 'testuser',
      password: 'testpass',
    };

    await expect(login(formData)).rejects.toMatchObject({
      message: 'Request failed (500)',
      status: 500,
    });
  });

  it('calls verifyEmail with correct payload', async () => {
    const mockResponse = {
      message: 'ok',
      access_token: 'token-123', // pragma: allowlist secret
      token_type: 'bearer',
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(JSON.stringify(mockResponse)),
    });

    const result = await verifyEmail('abc');
    expect(result).toEqual(mockResponse);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/verify-email'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: 'abc' }),
      })
    );
  });

  it('calls forgotPassword with correct payload', async () => {
    const mockResponse = { message: 'ok' };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(JSON.stringify(mockResponse)),
    });

    const result = await forgotPassword('test@example.com');
    expect(result).toEqual(mockResponse);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/forgot-password'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@example.com' }),
      })
    );
  });

  it('calls resetPassword with correct payload', async () => {
    const mockResponse = { message: 'ok' };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(JSON.stringify(mockResponse)),
    });

    const result = await resetPassword('tkn', 'newpassword123456');
    expect(result).toEqual(mockResponse);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/reset-password'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: 'tkn',
          new_password: 'newpassword123456', // pragma: allowlist secret
        }),
      })
    );
  });

  it('calls resendVerification with correct payload', async () => {
    const mockResponse = { message: 'ok' };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(JSON.stringify(mockResponse)),
    });

    const result = await resendVerification('test@example.com');
    expect(result).toEqual(mockResponse);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/resend-verification'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@example.com' }),
      })
    );
  });
});

describe('Register API', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', fetchMock);
  });

  it('handles successful registration', async () => {
    const mockToken = {
      access_token: 'test-registration-token',
      token_type: 'bearer' as const,
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 201,
      text: vi.fn().mockResolvedValue(JSON.stringify(mockToken)),
    });

    const formData: RegisterFormData = {
      username: 'newuser',
      email: 'newuser@example.com',
      password: 'securepassword123',
      confirmPassword: 'securepassword123',
      first_name: 'John',
      last_name: 'Doe',
    };

    const result = await register(formData);

    expect(result).toEqual(mockToken);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/register'),
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: 'newuser',
          email: 'newuser@example.com',
          password: 'securepassword123',
          first_name: 'John',
          last_name: 'Doe',
          // confirmPassword should be excluded
        }),
      })
    );
  });

  it('excludes confirmPassword from request body', async () => {
    const mockToken = {
      access_token: 'test-token',
      token_type: 'bearer' as const,
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 201,
      text: vi.fn().mockResolvedValue(JSON.stringify(mockToken)),
    });

    const formData: RegisterFormData = {
      username: 'testuser',
      email: 'test@example.com',
      password: 'password123456',
      confirmPassword: 'password123456',
    };

    await register(formData);

    const requestBody = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(requestBody).not.toHaveProperty('confirmPassword');
    expect(requestBody).toEqual({
      username: 'testuser',
      email: 'test@example.com',
      password: 'password123456',
    });
  });

  it('handles registration failure with 400 error (validation error)', async () => {
    const validationError = {
      detail: 'Username already exists',
    };

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: vi.fn().mockResolvedValue(JSON.stringify(validationError)),
    });

    const formData: RegisterFormData = {
      username: 'existinguser',
      email: 'test@example.com',
      password: 'password123456',
      confirmPassword: 'password123456',
    };

    await expect(register(formData)).rejects.toMatchObject({
      message: 'Username already exists',
      status: 400,
    });
  });

  it('handles registration failure with 409 error (conflict)', async () => {
    const conflictError = {
      detail: 'Email already registered',
    };

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 409,
      text: vi.fn().mockResolvedValue(JSON.stringify(conflictError)),
    });

    const formData: RegisterFormData = {
      username: 'newuser',
      email: 'existing@example.com',
      password: 'password123456',
      confirmPassword: 'password123456',
    };

    await expect(register(formData)).rejects.toMatchObject({
      message: 'Email already registered',
      status: 409,
    });
  });

  it('handles registration failure with 422 error (unprocessable entity)', async () => {
    const validationError = {
      detail: [
        {
          loc: ['body', 'email'],
          msg: 'field required',
          type: 'value_error.missing',
        },
      ],
    };

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 422,
      text: vi.fn().mockResolvedValue(JSON.stringify(validationError)),
    });

    const formData: RegisterFormData = {
      username: 'testuser',
      email: '',
      password: 'password123456',
      confirmPassword: 'password123456',
    };

    await expect(register(formData)).rejects.toMatchObject({
      status: 422,
    });
  });

  it('handles network errors', async () => {
    fetchMock.mockRejectedValueOnce(new Error('Network error'));

    const formData: RegisterFormData = {
      username: 'testuser',
      email: 'test@example.com',
      password: 'password123456',
      confirmPassword: 'password123456',
    };

    await expect(register(formData)).rejects.toThrow('Network error');
  });

  it('handles server errors with generic message', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: vi.fn().mockResolvedValue(JSON.stringify({})),
    });

    const formData: RegisterFormData = {
      username: 'testuser',
      email: 'test@example.com',
      password: 'password123456',
      confirmPassword: 'password123456',
    };

    await expect(register(formData)).rejects.toMatchObject({
      message: 'Request failed (500)',
      status: 500,
    });
  });

  it('handles error responses with message field instead of detail', async () => {
    const errorWithMessage = {
      message: 'Custom registration error',
    };

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: vi.fn().mockResolvedValue(JSON.stringify(errorWithMessage)),
    });

    const formData: RegisterFormData = {
      username: 'testuser',
      email: 'test@example.com',
      password: 'password123456',
      confirmPassword: 'password123456',
    };

    await expect(register(formData)).rejects.toMatchObject({
      message: 'Custom registration error',
      status: 400,
    });
  });
});
