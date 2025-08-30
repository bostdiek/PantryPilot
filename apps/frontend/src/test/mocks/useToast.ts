import { vi } from 'vitest';
import type { ToastState } from '../../components/ui/toast-utils';

// Function to create mock toast methods with reset ability for tests
export function createToastMock() {
  // Mock state that will be modified by the mock functions
  let toasts: ToastState[] = [];

  // Mock implementations
  const mockRemoveToast = vi.fn((id: string) => {
    toasts = toasts.filter((t) => t.id !== id);
  });

  const mockSuccess = vi.fn((message: string) => {
    const id = `toast-success-${Date.now()}`;
    toasts.push({ id, message, type: 'success' });
    return id;
  });

  const mockError = vi.fn((message: string) => {
    const id = `toast-error-${Date.now()}`;
    toasts.push({ id, message, type: 'error' });
    return id;
  });

  const mockInfo = vi.fn((message: string) => {
    const id = `toast-info-${Date.now()}`;
    toasts.push({ id, message, type: 'info' });
    return id;
  });

  const mockUseToast = vi.fn(() => ({
    toastList: toasts,
    removeToast: mockRemoveToast,
    success: mockSuccess,
    error: mockError,
    info: mockInfo,
  }));

  // Reset function to clear state between tests
  const resetMock = () => {
    toasts = [];
    mockRemoveToast.mockClear();
    mockSuccess.mockClear();
    mockError.mockClear();
    mockInfo.mockClear();
    mockUseToast.mockClear();
  };

  return {
    mock: mockUseToast,
    reset: resetMock,
    // Expose methods for direct access in tests if needed
    methods: {
      removeToast: mockRemoveToast,
      success: mockSuccess,
      error: mockError,
      info: mockInfo,
    },
  };
}

// Export a pre-created instance for convenience
export const toastMock = createToastMock();

// Export the mock for vi.mock
export const useToast = toastMock.mock;
