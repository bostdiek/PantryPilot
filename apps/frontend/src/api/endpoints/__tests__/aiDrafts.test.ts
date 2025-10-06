import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '../../client';
import {
  extractRecipeFromUrl,
  extractRecipeStream,
  getDraftById,
  getDraftByIdOwner,
} from '../aiDrafts';
import type {
  AIDraftFetchResponse,
  AIDraftResponse,
  SSEEvent,
} from '../../../types/AIDraft';
import { ApiErrorImpl } from '../../../types/api';

// Mock the API client
vi.mock('../../client', () => ({
  apiClient: {
    request: vi.fn(),
  },
  getApiBaseUrl: vi.fn(() => 'http://localhost:8000'),
}));

// Mock useAuthStore
vi.mock('../../../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: vi.fn(() => ({ token: 'test-token' })),
  },
}));

describe('AI Drafts API endpoints', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('extractRecipeFromUrl', () => {
    it('calls API with correct endpoint and data', async () => {
      const mockResponse: AIDraftResponse = {
        draft_id: 'draft-123',
        signed_url: '/recipes/new?ai=1&draftId=draft-123&token=jwt-token',
        expires_at: '2025-10-03T20:03:34.543240Z',
        ttl_seconds: 3600,
      };

      (apiClient.request as any).mockResolvedValueOnce(mockResponse);

      const result = await extractRecipeFromUrl(
        'https://example.com/recipe',
        undefined
      );

      expect(apiClient.request).toHaveBeenCalledWith(
        '/api/v1/ai/extract-recipe-from-url',
        {
          method: 'POST',
          body: JSON.stringify({
            source_url: 'https://example.com/recipe',
          }),
        }
      );
      expect(result).toEqual(mockResponse);
    });

    it('includes prompt_override when provided', async () => {
      const mockResponse: AIDraftResponse = {
        draft_id: 'draft-123',
        signed_url: '/recipes/new?ai=1&draftId=draft-123&token=jwt-token',
        expires_at: '2025-10-03T20:03:34.543240Z',
        ttl_seconds: 3600,
      };

      (apiClient.request as any).mockResolvedValueOnce(mockResponse);

      await extractRecipeFromUrl(
        'https://example.com/recipe',
        'custom prompt'
      );

      expect(apiClient.request).toHaveBeenCalledWith(
        '/api/v1/ai/extract-recipe-from-url',
        {
          method: 'POST',
          body: JSON.stringify({
            source_url: 'https://example.com/recipe',
            prompt_override: 'custom prompt',
          }),
        }
      );
    });

    it('handles API errors', async () => {
      const apiError = new ApiErrorImpl(
        'Invalid URL',
        422,
        'validation_error'
      );

      (apiClient.request as any).mockRejectedValueOnce(apiError);

      await expect(
        extractRecipeFromUrl('invalid-url', undefined)
      ).rejects.toThrow('Invalid URL');
    });
  });

  describe('getDraftById', () => {
    it('calls API with correct endpoint and token', async () => {
      const mockResponse: AIDraftFetchResponse = {
        payload: {
          generated_recipe: {
            recipe_data: {
              title: 'Test Recipe',
              description: 'Test description',
              ingredients: [],
              instructions: [],
              prep_time_minutes: 10,
              cook_time_minutes: 20,
              serving_min: 2,
              difficulty: 'easy',
              category: 'dinner',
            },
            confidence_score: 0.9,
            extraction_notes: null,
            source_url: 'https://example.com/recipe',
          },
          extraction_metadata: {
            source_url: 'https://example.com/recipe',
            extracted_at: '2025-10-03T19:03:34.543173+00:00',
            confidence_score: 0.9,
          },
        },
        type: 'recipe_suggestion',
        created_at: '2025-10-03T19:03:34.543173+00:00',
        expires_at: '2025-10-03T20:03:34.543173+00:00',
      };

      (apiClient.request as any).mockResolvedValueOnce(mockResponse);

      const result = await getDraftById('draft-123', 'jwt-token');

      expect(apiClient.request).toHaveBeenCalledWith(
        '/api/v1/ai/drafts/draft-123?token=jwt-token',
        {
          method: 'GET',
        }
      );
      expect(result).toEqual(mockResponse);
    });

    it('handles expired or invalid tokens', async () => {
      const apiError = new ApiErrorImpl('Token expired', 401, 'token_expired');

      (apiClient.request as any).mockRejectedValueOnce(apiError);

      await expect(getDraftById('draft-123', 'expired-token')).rejects.toThrow(
        'Token expired'
      );
    });
  });

  describe('getDraftByIdOwner', () => {
    it('calls authenticated endpoint without query token', async () => {
      const mockResponse: AIDraftFetchResponse = {
        payload: {
          generated_recipe: null,
          extraction_metadata: {
            source_url: 'https://example.com/recipe',
            extracted_at: '2025-10-03T19:03:34.543173+00:00',
            failure: {
              reason: 'No recipe found',
            },
          },
        },
        type: 'recipe_suggestion',
        created_at: '2025-10-03T19:03:34.543173+00:00',
        expires_at: '2025-10-03T20:03:34.543173+00:00',
      };

      (apiClient.request as any).mockResolvedValueOnce(mockResponse);

      const result = await getDraftByIdOwner('draft-123');

      expect(apiClient.request).toHaveBeenCalledWith(
        '/api/v1/ai/drafts/draft-123/me',
        {
          method: 'GET',
        }
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('extractRecipeStream', () => {
    let eventSourceMock: {
      close: ReturnType<typeof vi.fn>;
      addEventListener: ReturnType<typeof vi.fn>;
      removeEventListener: ReturnType<typeof vi.fn>;
      onmessage: ((evt: MessageEvent) => void) | null;
      onerror: ((evt: Event) => void) | null;
    };

    beforeEach(() => {
      eventSourceMock = {
        close: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onmessage: null,
        onerror: null,
      };

      // Mock EventSource constructor
      (globalThis as any).EventSource = vi.fn(
        () => eventSourceMock
      ) as unknown as typeof EventSource;
    });

    it('establishes SSE connection with correct URL', () => {
      const onProgress = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      extractRecipeStream(
        'https://example.com/recipe',
        undefined,
        onProgress,
        onComplete,
        onError
      );

      expect((globalThis as any).EventSource).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/ai/extract-recipe-stream?source_url=https%3A%2F%2Fexample.com%2Frecipe',
        { withCredentials: true }
      );
    });

    it('includes prompt_override in URL when provided', () => {
      const onProgress = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      extractRecipeStream(
        'https://example.com/recipe',
        'custom prompt',
        onProgress,
        onComplete,
        onError
      );

      // URLSearchParams uses + for spaces, not %20
      expect((globalThis as any).EventSource).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/ai/extract-recipe-stream?source_url=https%3A%2F%2Fexample.com%2Frecipe&prompt_override=custom+prompt',
        { withCredentials: true }
      );
    });

    it('handles progress events', () => {
      const onProgress = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      extractRecipeStream(
        'https://example.com/recipe',
        undefined,
        onProgress,
        onComplete,
        onError
      );

      const progressEvent: SSEEvent = {
        status: 'fetching',
        step: 'fetch_html',
        progress: 0.2,
        detail: 'Fetching page content...',
      };

      // Simulate SSE message
      eventSourceMock.onmessage?.({
        data: JSON.stringify(progressEvent),
      } as MessageEvent);

      expect(onProgress).toHaveBeenCalledWith(progressEvent);
      expect(onComplete).not.toHaveBeenCalled();
      expect(onError).not.toHaveBeenCalled();
    });

    it('handles complete event and navigates', () => {
      const onProgress = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      extractRecipeStream(
        'https://example.com/recipe',
        undefined,
        onProgress,
        onComplete,
        onError
      );

      const completeEvent: SSEEvent = {
        status: 'complete',
        step: 'complete',
        progress: 1.0,
        draft_id: 'draft-123',
        signed_url: '/recipes/new?ai=1&draftId=draft-123&token=jwt-token',
        success: true,
      };

      eventSourceMock.onmessage?.({
        data: JSON.stringify(completeEvent),
      } as MessageEvent);

      expect(onProgress).toHaveBeenCalledWith(completeEvent);
      expect(onComplete).toHaveBeenCalledWith(
        '/recipes/new?ai=1&draftId=draft-123&token=jwt-token',
        'draft-123'
      );
      expect(eventSourceMock.close).toHaveBeenCalled();
    });

    it('handles error event', () => {
      const onProgress = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      extractRecipeStream(
        'https://example.com/recipe',
        undefined,
        onProgress,
        onComplete,
        onError
      );

      const errorEvent: SSEEvent = {
        status: 'error',
        step: 'ai_call',
        detail: 'AI model failed to extract recipe',
        error_code: 'model_error',
      };

      eventSourceMock.onmessage?.({
        data: JSON.stringify(errorEvent),
      } as MessageEvent);

      expect(onProgress).toHaveBeenCalledWith(errorEvent);
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'AI model failed to extract recipe',
          code: 'model_error',
        })
      );
      expect(eventSourceMock.close).toHaveBeenCalled();
    });

    it('handles connection errors', () => {
      const onProgress = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      extractRecipeStream(
        'https://example.com/recipe',
        undefined,
        onProgress,
        onComplete,
        onError
      );

      eventSourceMock.onerror?.(new Event('error'));

      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Connection to server lost',
          code: 'connection_error',
        })
      );
      expect(eventSourceMock.close).toHaveBeenCalled();
    });
  });
});
