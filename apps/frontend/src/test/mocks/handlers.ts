import { HttpResponse, http } from 'msw';

// Define handlers for different API endpoints
export const handlers = [
  // Health check endpoint
  http.get('*/api/v1/health', () => {
    return HttpResponse.json({
      data: {
        status: 'healthy',
        message: 'API is operational',
        timestamp: new Date().toISOString(),
      },
    });
  }),

  // Mock 500 error example
  http.get('*/api/v1/health/error', () => {
    return new HttpResponse(
      JSON.stringify({
        error: 'Internal server error',
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }),

  // Network error example (used in tests)
  http.get('*/api/v1/health/network-error', () => {
    return HttpResponse.error();
  }),

  // Generic test endpoint for client tests
  http.get('*/test-endpoint', () => {
    return HttpResponse.json({
      data: { message: 'Success' },
    });
  }),
];
