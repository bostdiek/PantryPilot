import { useCallback, useState } from 'react';
import type { ApiError } from '../types/api';

interface UseApiOptions<T> {
  initialData?: T;
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
}

export function useApi<T, TArgs extends any[]>(
  apiFunction: (...args: TArgs) => Promise<T>,
  options: UseApiOptions<T> = {}
) {
  // Destructure option callbacks so we don't capture a new `options` object
  // on every render (which would invalidate the execute callback).
  const { initialData, onSuccess, onError } = options;

  const [data, setData] = useState<T | null>(initialData || null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);

  const execute = useCallback(
    async (...args: TArgs) => {
      try {
        setLoading(true);
        setError(null);
        const result = await apiFunction(...args);
        setData(result);
        onSuccess?.(result);
        return result;
      } catch (err) {
        const apiError = err as ApiError;
        setError(apiError);
        onError?.(apiError);
        throw apiError;
      } finally {
        setLoading(false);
      }
    },
    [apiFunction, onSuccess, onError]
  );

  return {
    data,
    error,
    loading,
    execute,
  };
}
