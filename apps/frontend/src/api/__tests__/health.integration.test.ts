import { HttpResponse, http } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { server } from '../../test/mocks/server';
import { healthCheck } from '../endpoints/health';

describe('Health API - Integration Tests with MSW', () => {
  beforeEach(() => vi.clearAllMocks());

  it('retrieves health status successfully', async () => {
    server.use(
      http.get('*/api/v1/health', () =>
        HttpResponse.json({
          success: true,
          data: {
            status: 'healthy',
            message: 'Integration test successful',
            timestamp: '2025-08-22T12:00:00Z',
          },
          message: 'Health check successful',
          error: null,
        })
      )
    );

    const result = await healthCheck();

    expect(result).toEqual({
      status: 'healthy',
      message: 'Integration test successful',
      timestamp: '2025-08-22T12:00:00Z',
    });
  });

  it('propagates server error responses', async () => {
    server.use(
      http.get(
        '*/api/v1/health',
        () =>
          new HttpResponse(
            JSON.stringify({
              success: false,
              data: null,
              message: 'Server is down',
              error: { code: 'SERVER_ERROR' },
            }),
            {
              status: 500,
            }
          )
      )
    );

    await expect(healthCheck()).rejects.toHaveProperty('message');
  });

  it('handles network errors', async () => {
    server.use(http.get('*/api/v1/health', () => HttpResponse.error()));

    await expect(healthCheck()).rejects.toHaveProperty('message');
  });
});
