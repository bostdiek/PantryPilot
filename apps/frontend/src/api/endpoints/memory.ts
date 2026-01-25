import type { MemoryDocument, MemoryUpdate } from '../../types/Memory';
import { apiClient } from '../client';

export const memoryApi = {
  /**
   * Get current user's memory document
   */
  async getMemory(): Promise<MemoryDocument> {
    return apiClient.request<MemoryDocument>('/api/v1/chat/memory');
  },

  /**
   * Update current user's memory document
   */
  async updateMemory(update: MemoryUpdate): Promise<MemoryDocument> {
    return apiClient.request<MemoryDocument>('/api/v1/chat/memory', {
      method: 'PUT',
      body: JSON.stringify(update),
    });
  },
};
