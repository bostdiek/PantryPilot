import { beforeEach, describe, expect, it, vi } from 'vitest';
import { login } from '../endpoints/auth';
import type { LoginFormData } from '../../types/auth';

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
});