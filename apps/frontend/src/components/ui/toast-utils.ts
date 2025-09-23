// Shared state and utilities for toast functionality
export interface ToastState {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
  // Optional timestamp (ms since epoch). If not provided, callers may rely on
  // the system to set it when adding a toast. Used to enable time-based
  // deduplication so the same message can reappear after a short window.
  createdAt?: number;
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
  // Ensure toasts have a createdAt timestamp to support time-based dedup.
  if (!toast.createdAt) {
    // non-mutating callers may rely on the object they passed; create a
    // shallow copy to avoid surprising external mutations.
    toast = { ...toast, createdAt: Date.now() };
  }
  internalToasts.push(toast);
  notifyListeners();
}

/**
 * Add a toast unless an equivalent toast (same message and type) already exists.
 *
 * Prevents duplicate notifications when the same error or info message is
 * reported multiple times in quick succession.
 *
 * @param {ToastState} toast - The toast to add (shape: { id, message, type }).
 * @example
 * // Add an error toast only if not already present
 * addToastIfNotExists({ id: generateToastId(), message: 'Session expired', type: 'error' });
 */
/**
 * Add a toast unless an equivalent toast already exists within a time window.
 *
 * By default, prevents duplicate notifications with the same message + type
 * appearing within 5 seconds. Callers may pass `dedupWindowMs` to change
 * the window or pass 0 to disable time-based deduplication and rely only on
 * message+type uniqueness.
 */
export function addToastIfNotExists(toast: ToastState, dedupWindowMs = 5000) {
  const now = Date.now();
  const existingToast = internalToasts.find((t) => {
    if (t.message !== toast.message || t.type !== toast.type) return false;
    if (!dedupWindowMs) return true; // treat any match as duplicate
    const created = t.createdAt ?? now;
    return now - created < dedupWindowMs;
  });

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
