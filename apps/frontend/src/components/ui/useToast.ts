import { useEffect, useState } from 'react';
import {
  addToast,
  generateToastId,
  removeToast as removeToastUtil,
  toastListeners,
  type ToastState,
} from './toast-utils';

export function useToast() {
  const [toastList, setToastList] = useState<ToastState[]>([]);

  useEffect(() => {
    const listener = (newToasts: ToastState[]) => setToastList(newToasts);
    toastListeners.add(listener);
    return () => {
      toastListeners.delete(listener);
    };
  }, []);

  const showToast = (
    message: string,
    type: 'success' | 'error' | 'info' = 'success'
  ) => {
    const id = generateToastId();
    const newToast = { id, message, type };
    addToast(newToast);

    // Auto-remove after duration
    setTimeout(() => {
      removeToastUtil(id);
    }, 4300); // Slightly longer than Toast duration to account for exit animation
  };

  const removeToast = (id: string) => {
    removeToastUtil(id);
  };

  return {
    toastList,
    showToast,
    removeToast,
    success: (message: string) => showToast(message, 'success'),
    error: (message: string) => showToast(message, 'error'),
    info: (message: string) => showToast(message, 'info'),
  };
}
