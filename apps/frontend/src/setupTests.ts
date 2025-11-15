import { mockAnimationsApi } from 'jsdom-testing-mocks';
import { webcrypto as nodeWebcrypto } from 'node:crypto';
import { vi } from 'vitest';

// Polyfill Web Crypto for test runtime if missing (fixes crypto.getRandomValues error)
if (
  typeof globalThis.crypto === 'undefined' ||
  typeof (globalThis as any).crypto?.getRandomValues !== 'function'
) {
  // Assign Node's Web Crypto to the global for tests

  (globalThis as any).crypto = nodeWebcrypto as unknown as Crypto;
}

// Polyfill window.matchMedia for jsdom in test environments. Some hooks and
// components branch on media queries (mobile vs desktop). Providing a
// deterministic implementation prevents CI from rendering different DOM
// trees compared to local runs.
if (typeof (window as any).matchMedia === 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  });
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
