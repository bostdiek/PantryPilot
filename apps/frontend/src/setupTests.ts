import { mockAnimationsApi } from 'jsdom-testing-mocks';
import { vi } from 'vitest';

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
