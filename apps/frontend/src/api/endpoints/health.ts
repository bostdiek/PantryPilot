import type { HealthCheckResponse } from '../../types/api';
import { apiClient } from '../client';

export async function healthCheck(): Promise<HealthCheckResponse> {
  return apiClient.request<HealthCheckResponse>('/api/v1/health', {
    method: 'GET',
  });
}
