import { Toast } from './Toast';
import { useToast } from './useToast';

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
          testId={toast.id}
        />
      ))}
    </div>
  );
}
