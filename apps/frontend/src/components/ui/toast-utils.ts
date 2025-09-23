// Shared state and utilities for toast functionality
export interface ToastState {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

let toastId = 0;
export const toastListeners = new Set<(toasts: ToastState[]) => void>();
let internalToasts: ToastState[] = [];

export function getToasts(): ToastState[] {
  return [...internalToasts];
}

export function notifyListeners() {
  toastListeners.forEach((listener) => listener(getToasts()));
}

export function addToast(toast: ToastState) {
  internalToasts.push(toast);
  notifyListeners();
}

/**
 * Add a toast if one with the same message doesn't already exist.
 * Useful for preventing duplicate notifications.
 */
export function addToastIfNotExists(toast: ToastState) {
  const existingToast = internalToasts.find(t => t.message === toast.message && t.type === toast.type);
  if (!existingToast) {
    addToast(toast);
  }
}

export function removeToast(id: string) {
  internalToasts = internalToasts.filter((t) => t.id !== id);
  notifyListeners();
}

export function generateToastId() {
  return `toast-${++toastId}`;
}
