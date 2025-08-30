import { vi } from 'vitest';
import type { ToastState } from '../components/ui/toast-utils';

// Shared toast state that persists between test runs
let toasts: ToastState[] = [];

// Reset function for between tests
export const resetToastMock = () => {
  toasts = [];
  mockUseToast.mockClear();
  mockSuccess.mockClear();
  mockError.mockClear();
  mockInfo.mockClear();
  mockRemoveToast.mockClear();
};

// Mock implementation functions
const mockRemoveToast = vi.fn((id: string) => {
  toasts = toasts.filter((t) => t.id !== id);
});

const mockSuccess = vi.fn((message: string) => {
  const id = `toast-success-test`;
  // Replace any existing success toast to avoid test conflicts
  toasts = toasts.filter((t) => t.id !== id);
  toasts.push({ id, message, type: 'success' });
  return id;
});

const mockError = vi.fn((message: string) => {
  const id = `toast-error-test`;
  // Replace any existing error toast to avoid test conflicts
  toasts = toasts.filter((t) => t.id !== id);
  toasts.push({ id, message, type: 'error' });
  return id;
});

const mockInfo = vi.fn((message: string) => {
  const id = `toast-info-test`;
  // Replace any existing info toast to avoid test conflicts
  toasts = toasts.filter((t) => t.id !== id);
  toasts.push({ id, message, type: 'info' });
  return id;
});

// The main mock function
const mockUseToast = vi.fn(() => ({
  toastList: toasts,
  removeToast: mockRemoveToast,
  success: mockSuccess,
  error: mockError,
  info: mockInfo,
}));

export const useToast = mockUseToast;
