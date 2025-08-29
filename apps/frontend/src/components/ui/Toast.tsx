import { useEffect, useState } from 'react';
import { Icon } from './Icon';
import checkIcon from './icons/check.svg?react';

export interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info';
  duration?: number;
  onClose?: () => void;
}

export function Toast({ message, type = 'success', duration = 4000, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(() => {
        setIsVisible(false);
        onClose?.();
      }, 300); // Exit animation duration
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!isVisible) return null;

  const bgColor = type === 'success' ? 'bg-green-50' : type === 'error' ? 'bg-red-50' : 'bg-blue-50';
  const borderColor = type === 'success' ? 'border-green-200' : type === 'error' ? 'border-red-200' : 'border-blue-200';
  const textColor = type === 'success' ? 'text-green-800' : type === 'error' ? 'text-red-800' : 'text-blue-800';
  const iconColor = type === 'success' ? 'text-green-400' : type === 'error' ? 'text-red-400' : 'text-blue-400';

  return (
    <div
      className={`fixed top-4 right-4 z-50 max-w-md w-full ${bgColor} border ${borderColor} rounded-lg shadow-lg p-4 transition-all duration-300 ${
        isExiting ? 'transform translate-x-full opacity-0' : 'transform translate-x-0 opacity-100'
      }`}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start">
        <div className={`flex-shrink-0 ${iconColor}`}>
          <Icon svg={checkIcon} className="h-5 w-5" />
        </div>
        <div className={`ml-3 ${textColor}`}>
          <p className="text-sm font-medium">{message}</p>
        </div>
        <div className="ml-auto pl-3">
          <button
            type="button"
            className={`inline-flex rounded-md ${bgColor} ${textColor} hover:${textColor} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500`}
            onClick={() => {
              setIsExiting(true);
              setTimeout(() => {
                setIsVisible(false);
                onClose?.();
              }, 300);
            }}
          >
            <span className="sr-only">Dismiss</span>
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

// Hook for managing toasts
interface ToastState {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

let toastId = 0;
const toastListeners = new Set<(toasts: ToastState[]) => void>();
let toasts: ToastState[] = [];

function notifyListeners() {
  toastListeners.forEach(listener => listener([...toasts]));
}

export function useToast() {
  const [toastList, setToastList] = useState<ToastState[]>([]);

  useEffect(() => {
    const listener = (newToasts: ToastState[]) => setToastList(newToasts);
    toastListeners.add(listener);
    return () => toastListeners.delete(listener);
  }, []);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    const id = `toast-${++toastId}`;
    const newToast = { id, message, type };
    toasts.push(newToast);
    notifyListeners();

    // Auto-remove after duration
    setTimeout(() => {
      toasts = toasts.filter(t => t.id !== id);
      notifyListeners();
    }, 4300); // Slightly longer than Toast duration to account for exit animation
  };

  const removeToast = (id: string) => {
    toasts = toasts.filter(t => t.id !== id);
    notifyListeners();
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

// Toast Container Component
export function ToastContainer() {
  const { toastList, removeToast } = useToast();

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toastList.map((toast) => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );
}