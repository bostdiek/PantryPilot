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

export function removeToast(id: string) {
  internalToasts = internalToasts.filter((t) => t.id !== id);
  notifyListeners();
}

export function generateToastId() {
  return `toast-${++toastId}`;
}
