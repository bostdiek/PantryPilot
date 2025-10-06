import { apiClient } from '../client';
import type {
  AIDraftFetchResponse,
  AIDraftResponse,
  SSEEvent,
} from '../../types/AIDraft';
import { ApiErrorImpl } from '../../types/api';
import { useAuthStore } from '../../stores/useAuthStore';

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
  const url = `/api/v1/ai/extract-recipe-stream?${params.toString()}`;

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
      console.error('Failed to parse SSE message:', err);
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
    console.error('SSE connection error:', evt);
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

  try {
    const response = await fetch(
      `/api/v1/ai/extract-recipe-stream?${params.toString()}`,
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
      onError(
        new ApiErrorImpl('No response body', undefined, 'no_body')
      );
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
            break;
          } else if (data.status === 'error') {
            onError(
              new ApiErrorImpl(
                data.detail || 'Extraction failed',
                undefined,
                data.error_code
              )
            );
            break;
          }
        } catch (err) {
          console.error('Failed to parse SSE message:', err);
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
