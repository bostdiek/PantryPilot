import { webcrypto as nodeWebcrypto } from 'node:crypto';
import { mockAnimationsApi } from 'jsdom-testing-mocks';
import { vi } from 'vitest';

// Polyfill Web Crypto for test runtime if missing (fixes crypto.getRandomValues error)
if (
  typeof globalThis.crypto === 'undefined' ||
  typeof (globalThis as any).crypto?.getRandomValues !== 'function'
) {
  // Assign Node's Web Crypto to the global for tests

  (globalThis as any).crypto = nodeWebcrypto as unknown as Crypto;
}

// Setup animation mock for Headless UI
mockAnimationsApi();

// Mock the useToast hook
vi.mock('./components/ui/useToast', () => ({
  useToast: () => ({
    toastList: [],
    removeToast: vi.fn(),
    showToast: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

// Also mock from the Toast import path since some components import from there
vi.mock('./components/ui/Toast', async () => {
  const actual = await vi.importActual('./components/ui/Toast');
  return {
    ...actual,
    useToast: () => ({
      toastList: [],
      removeToast: vi.fn(),
      showToast: vi.fn(),
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
    }),
  };
});
