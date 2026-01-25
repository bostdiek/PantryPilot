import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock api client
vi.mock('../../client', () => {
  const request = vi.fn();
  return {
    apiClient: { request },
    getApiBaseUrl: () => 'http://api',
  };
});

// Helper to access the mocked apiClient.request spy
const getMockRequest = async () => {
  const mod = await import('../../client');
  return mod.apiClient.request as ReturnType<typeof vi.fn>;
};

import { memoryApi } from '../memory';

describe('memory endpoints', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getMemory', () => {
    it('calls apiClient with GET', async () => {
      const mockRequest = await getMockRequest();
      const mockDoc = {
        content: '## Memory',
        format: 'markdown' as const,
        version: 1,
        updated_at: '2026-01-24T12:00:00Z',
        updated_by: 'assistant' as const,
      };
      mockRequest.mockResolvedValueOnce(mockDoc);

      const res = await memoryApi.getMemory();

      expect(mockRequest).toHaveBeenCalledWith('/api/v1/chat/memory');
      expect(res).toEqual(mockDoc);
    });
  });

  describe('updateMemory', () => {
    it('calls apiClient with PUT and body', async () => {
      const mockRequest = await getMockRequest();
      const mockDoc = {
        content: '## Updated Memory',
        format: 'markdown' as const,
        version: 2,
        updated_at: '2026-01-24T13:00:00Z',
        updated_by: 'user' as const,
      };
      mockRequest.mockResolvedValueOnce(mockDoc);

      const res = await memoryApi.updateMemory({
        content: '## Updated Memory',
      });

      expect(mockRequest).toHaveBeenCalledWith('/api/v1/chat/memory', {
        method: 'PUT',
        body: JSON.stringify({ content: '## Updated Memory' }),
      });
      expect(res).toEqual(mockDoc);
    });
  });
});
