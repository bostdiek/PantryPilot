import { apiClient } from './client';

export interface HealthStatus {
  status: string;
  message: string;
}

export const healthService = {
  /**
   * Check if the API is healthy and reachable
   */
  async checkHealth(): Promise<HealthStatus> {
    return apiClient.healthCheck();
  },
};
