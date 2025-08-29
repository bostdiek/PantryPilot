import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { server } from './mocks/server';

// Establish API mocking before all tests
// Use 'bypass' for unhandled requests to allow unit tests to work with fetch mocking
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished
afterAll(() => server.close());

// Filter noisy console errors in tests without altering behavior
const realConsoleError = console.error;
beforeAll(() => {
  vi.spyOn(console, 'error').mockImplementation((...args: unknown[]) => {
    const first = args[0];
    if (
      typeof first === 'string' &&
      (first.includes(
        'Invalid prop `data-headlessui-state` supplied to `React.Fragment`'
      ) ||
        first.includes('Not implemented: navigation'))
    ) {
      return; // suppress known jsdom/headlessui noise
    }
    // Forward other console errors
    (realConsoleError as unknown as (...a: unknown[]) => void)(...args);
  });
});

afterAll(() => {
  // Restore console after tests complete
  (console.error as unknown as { mockRestore: () => void }).mockRestore?.();
});

// SVG imports are mocked via Vite test-only alias in vite.config.ts
