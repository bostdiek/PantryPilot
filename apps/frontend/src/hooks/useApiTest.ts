import { useState } from 'react';
import { healthService } from '../api/health';

export interface ApiTestState {
  status: string;
  isLoading: boolean;
  error: string | null;
}

export const useApiTest = () => {
  const [state, setState] = useState<ApiTestState>({
    status: '',
    isLoading: false,
    error: null,
  });

  const testConnection = async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const health = await healthService.checkHealth();
      setState({
        status: `✅ API Connected: ${health.message}`,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      setState({
        status: `❌ API Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  return {
    ...state,
    testConnection,
  };
};
