import { logger } from '../../lib/logger';
import { useAuthStore } from '../../stores/useAuthStore';
import type {
  AIDraftFetchResponse,
  AIDraftResponse,
  SSEEvent,
} from '../../types/AIDraft';
import { ApiErrorImpl } from '../../types/api';
import { apiClient, getApiBaseUrl } from '../client';

/**
 * AI Drafts API endpoints
 * Handles recipe extraction from URLs with streaming SSE support
 */

/**
 * Extract recipe from URL using Server-Sent Events (SSE) for progress updates.
 * This is the preferred method for better UX with progress feedback.
 *
 * @param sourceUrl - The URL to extract the recipe from
 * @param promptOverride - Optional custom prompt to override default extraction
 * @param onProgress - Callback for progress updates
 * @param onComplete - Callback for completion with signed_url
 * @param onError - Callback for error handling
 * @returns EventSource instance that can be closed to cancel the request
 */
export function extractRecipeStream(
  sourceUrl: string,
  promptOverride: string | undefined,
  onProgress: (event: SSEEvent) => void,
  onComplete: (signedUrl: string, draftId: string) => void,
  onError: (error: ApiErrorImpl) => void
): EventSource {
  // Build URL with query parameters
  const params = new URLSearchParams({
    source_url: sourceUrl,
  });

  if (promptOverride) {
    params.append('prompt_override', promptOverride);
  }

  // For SSE with EventSource, we need to include credentials
  // Note: EventSource doesn't support custom headers, so we rely on cookie-based auth
  // or the backend accepts Bearer token in query params (check backend implementation)
  // Use full URL from apiClient base URL
  const API_BASE_URL = getApiBaseUrl();
  const url = `${API_BASE_URL}/api/v1/ai/extract-recipe-stream?${params.toString()}`;

  const eventSource = new EventSource(url, { withCredentials: true });

  eventSource.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data) as SSEEvent;

      // Call progress callback for all events
      onProgress(data);

      // Handle terminal events
      if (data.status === 'complete') {
        if (data.signed_url && data.draft_id) {
          onComplete(data.signed_url, data.draft_id);
        } else {
          onError(
            new ApiErrorImpl(
              'Extraction completed but missing signed_url or draft_id',
              undefined,
              'invalid_response'
            )
          );
        }
        eventSource.close();
      } else if (data.status === 'error') {
        onError(
          new ApiErrorImpl(
            data.detail || 'Extraction failed',
            undefined,
            data.error_code
          )
        );
        eventSource.close();
      }
    } catch (err) {
      logger.error('Failed to parse SSE message:', err);
      onError(
        new ApiErrorImpl(
          'Failed to parse server message',
          undefined,
          'parse_error',
          undefined,
          err instanceof Error ? err : undefined
        )
      );
      eventSource.close();
    }
  };

  eventSource.onerror = (evt) => {
    logger.error('SSE connection error:', evt);
    onError(
      new ApiErrorImpl(
        'Connection to server lost',
        undefined,
        'connection_error'
      )
    );
    eventSource.close();
  };

  return eventSource;
}

/**
 * Extract recipe from URL using standard POST request (fallback method).
 * Use this when SSE is not available or as a fallback.
 *
 * @param sourceUrl - The URL to extract the recipe from
 * @param promptOverride - Optional custom prompt to override default extraction
 * @returns Promise with the draft response containing signed_url
 */
export async function extractRecipeFromUrl(
  sourceUrl: string,
  promptOverride?: string
): Promise<AIDraftResponse> {
  const body: { source_url: string; prompt_override?: string } = {
    source_url: sourceUrl,
  };

  if (promptOverride) {
    body.prompt_override = promptOverride;
  }

  return apiClient.request<AIDraftResponse>(
    '/api/v1/ai/extract-recipe-from-url',
    {
      method: 'POST',
      body: JSON.stringify(body),
    }
  );
}

/**
 * Fetch an AI draft by ID using the signed token from the deep link.
 * This is the public route for loading drafts via signed URLs.
 *
 * @param draftId - The UUID of the draft
 * @param token - The signed JWT token from the deep link
 * @returns Promise with the draft payload
 */
export async function getDraftById(
  draftId: string,
  token: string
): Promise<AIDraftFetchResponse> {
  return apiClient.request<AIDraftFetchResponse>(
    `/api/v1/ai/drafts/${draftId}?token=${encodeURIComponent(token)}`,
    {
      method: 'GET',
    }
  );
}

/**
 * Fetch an AI draft by ID for the authenticated owner.
 * This is the owner-only route that uses Bearer token auth.
 *
 * @param draftId - The UUID of the draft
 * @returns Promise with the draft payload
 */
export async function getDraftByIdOwner(
  draftId: string
): Promise<AIDraftFetchResponse> {
  return apiClient.request<AIDraftFetchResponse>(
    `/api/v1/ai/drafts/${draftId}/me`,
    {
      method: 'GET',
    }
  );
}

/**
 * Alternative SSE implementation using fetch with ReadableStream for better header control.
 * This can be used when EventSource doesn't work due to auth header requirements.
 *
 * @param sourceUrl - The URL to extract the recipe from
 * @param promptOverride - Optional custom prompt to override default extraction
 * @param onProgress - Callback for progress updates
 * @param onComplete - Callback for completion with signed_url
 * @param onError - Callback for error handling
 * @returns AbortController that can be used to cancel the request
 */
export async function extractRecipeStreamFetch(
  sourceUrl: string,
  promptOverride: string | undefined,
  onProgress: (event: SSEEvent) => void,
  onComplete: (signedUrl: string, draftId: string) => void,
  onError: (error: ApiErrorImpl) => void
): Promise<AbortController> {
  const params = new URLSearchParams({
    source_url: sourceUrl,
  });

  if (promptOverride) {
    params.append('prompt_override', promptOverride);
  }

  const abortController = new AbortController();
  const token = useAuthStore.getState().token;
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const API_BASE_URL = getApiBaseUrl();

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/ai/extract-recipe-stream?${params.toString()}`,
      {
        method: 'GET',
        headers,
        credentials: 'include',
        signal: abortController.signal,
      }
    );

    if (!response.ok) {
      onError(
        new ApiErrorImpl(
          `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          'http_error'
        )
      );
      return abortController;
    }

    if (!response.body) {
      onError(new ApiErrorImpl('No response body', undefined, 'no_body'));
      return abortController;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    // Process the stream
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete messages (SSE format uses \n\n as delimiter)
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n\n')) !== -1) {
        const chunk = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 2);

        if (!chunk || !chunk.startsWith('data: ')) {
          continue;
        }

        // Extract JSON from SSE data: line
        const jsonStr = chunk.slice(6); // Remove "data: " prefix

        try {
          const data = JSON.parse(jsonStr) as SSEEvent;
          onProgress(data);

          if (data.status === 'complete') {
            // SSE streaming returns draft_id only (not signed_url)
            // The signed_url is only returned from the POST endpoint
            if (data.draft_id) {
              // For streaming, we have the draft_id but no signed_url
              // Pass empty string for signed_url - the caller will fetch the draft using getDraftByIdOwner
              onComplete('', data.draft_id);
              // Close the reader to stop processing further messages
              reader.cancel();
            } else {
              onError(
                new ApiErrorImpl(
                  'Extraction completed but missing draft_id',
                  undefined,
                  'invalid_response'
                )
              );
            }
            break;
          } else if (data.status === 'error') {
            onError(
              new ApiErrorImpl(
                data.detail || 'Extraction failed',
                undefined,
                data.error_code
              )
            );
            reader.cancel();
            break;
          }
        } catch (err) {
          logger.error('Failed to parse SSE message:', err);
        }
      }
    }
  } catch (err) {
    if ((err as Error).name === 'AbortError') {
      // Request was cancelled, don't call onError
      return abortController;
    }

    onError(
      new ApiErrorImpl(
        'Stream request failed',
        undefined,
        'stream_error',
        undefined,
        err instanceof Error ? err : undefined
      )
    );
  }

  return abortController;
}

/**
 * Extract recipe from image using Server-Sent Events (SSE) for progress updates.
 * This is the preferred method for better UX with progress feedback.
 * Uses fetch-based approach for better header control (auth tokens).
 *
 * @param file - The image file to extract the recipe from
 * @param promptOverride - Optional custom prompt to override default extraction
 * @param onProgress - Callback for progress updates
 * @param onComplete - Callback for completion with signed_url and draft_id
 * @param onError - Callback for error handling
 * @returns AbortController that can be used to cancel the request
 */
export async function extractRecipeFromImageStream(
  file: File,
  promptOverride: string | undefined,
  onProgress: (event: SSEEvent) => void,
  onComplete: (signedUrl: string, draftId: string) => void,
  onError: (error: ApiErrorImpl) => void
): Promise<AbortController> {
  const abortController = new AbortController();
  const token = useAuthStore.getState().token;

  // Create FormData for multipart upload
  const formData = new FormData();
  formData.append('file', file);
  if (promptOverride) {
    formData.append('prompt_override', promptOverride);
  }

  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // Note: Do NOT set Content-Type header - browser will set it with boundary for multipart/form-data

  const API_BASE_URL = getApiBaseUrl();

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/ai/extract-recipe-from-image-stream`,
      {
        method: 'POST',
        headers,
        body: formData,
        credentials: 'include',
        signal: abortController.signal,
      }
    );

    if (!response.ok) {
      // Handle specific error codes
      if (response.status === 413) {
        onError(
          new ApiErrorImpl(
            'File size is too large. Please use a smaller image.',
            response.status,
            'file_too_large'
          )
        );
      } else if (response.status === 415) {
        onError(
          new ApiErrorImpl(
            'Unsupported file type. Please upload an image file (JPEG, PNG, etc.).',
            response.status,
            'unsupported_media_type'
          )
        );
      } else {
        onError(
          new ApiErrorImpl(
            `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            'http_error'
          )
        );
      }
      return abortController;
    }

    if (!response.body) {
      onError(new ApiErrorImpl('No response body', undefined, 'no_body'));
      return abortController;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    // Process the stream
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete messages (SSE format uses \n\n as delimiter)
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n\n')) !== -1) {
        const chunk = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 2);

        if (!chunk || !chunk.startsWith('data: ')) {
          continue;
        }

        // Extract JSON from SSE data: line
        const jsonStr = chunk.slice(6); // Remove "data: " prefix

        try {
          const data = JSON.parse(jsonStr) as SSEEvent;
          onProgress(data);

          if (data.status === 'complete') {
            // SSE streaming returns draft_id only (not signed_url)
            // The signed_url is only returned from the POST endpoint
            if (data.draft_id) {
              // For streaming, we have the draft_id but no signed_url
              // Pass empty string for signed_url - the caller will fetch the draft using getDraftByIdOwner
              onComplete('', data.draft_id);
              // Close the reader to stop processing further messages
              reader.cancel();
            } else {
              onError(
                new ApiErrorImpl(
                  'Extraction completed but missing draft_id',
                  undefined,
                  'invalid_response'
                )
              );
            }
            break;
          } else if (data.status === 'error') {
            onError(
              new ApiErrorImpl(
                data.detail || 'Extraction failed',
                undefined,
                data.error_code
              )
            );
            reader.cancel();
            break;
          }
        } catch (err) {
          logger.error('Failed to parse SSE message:', err);
        }
      }
    }
  } catch (err) {
    if ((err as Error).name === 'AbortError') {
      // Request was cancelled, don't call onError
      return abortController;
    }

    onError(
      new ApiErrorImpl(
        'Stream request failed',
        undefined,
        'stream_error',
        undefined,
        err instanceof Error ? err : undefined
      )
    );
  }

  return abortController;
}

/**
 * Extract recipe from image using standard POST request (fallback method).
 * Use this when SSE is not available or as a fallback.
 *
 * @param file - The image file to extract the recipe from
 * @param promptOverride - Optional custom prompt to override default extraction
 * @returns Promise with the draft response containing signed_url
 */
export async function extractRecipeFromImage(
  file: File,
  promptOverride?: string
): Promise<AIDraftResponse> {
  // Create FormData for multipart upload
  const formData = new FormData();
  formData.append('file', file);
  if (promptOverride) {
    formData.append('prompt_override', promptOverride);
  }

  // Use apiClient but pass FormData directly
  // The apiClient should handle FormData without stringifying
  const token = useAuthStore.getState().token;
  const API_BASE_URL = getApiBaseUrl();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // Note: Do NOT set Content-Type header - fetch will set it with boundary for multipart/form-data

  const response = await fetch(
    `${API_BASE_URL}/api/v1/ai/extract-recipe-from-image`,
    {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    }
  );

  if (!response.ok) {
    // Handle specific error codes
    if (response.status === 413) {
      throw new ApiErrorImpl(
        'File size is too large. Please use a smaller image.',
        response.status,
        'file_too_large'
      );
    } else if (response.status === 415) {
      throw new ApiErrorImpl(
        'Unsupported file type. Please upload an image file (JPEG, PNG, etc.).',
        response.status,
        'unsupported_media_type'
      );
    }

    const body = await response.json().catch(() => ({}));
    throw new ApiErrorImpl(
      body.error || body.message || `HTTP ${response.status}`,
      response.status,
      'http_error'
    );
  }

  const body = await response.json();
  return body.data as AIDraftResponse;
}
