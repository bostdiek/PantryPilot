/**
 * Chat API endpoints for streaming chat and conversation history.
 *
 * Implements SSE streaming using fetch + ReadableStream pattern for
 * proper Authorization header support.
 */

import { logger } from '../../lib/logger';
import { useAuthStore } from '../../stores/useAuthStore';
import { ApiErrorImpl } from '../../types/api';
import type {
  ChatContentBlock,
  ChatSseEvent,
  ChatStreamCallbacks,
  ConversationListResponse,
  MessageHistoryResponse,
} from '../../types/Chat';
import { getApiBaseUrl } from '../client';

/**
 * Gets auth headers for API requests.
 */
function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// -----------------------------------------------------------------------------
// Streaming Chat API
// -----------------------------------------------------------------------------

/**
 * Stream a chat message to the backend and receive SSE events.
 *
 * Uses fetch + ReadableStream pattern for proper auth header support.
 * Follows the pattern from aiDrafts.ts extractRecipeStreamFetch.
 *
 * @param conversationId - Optional conversation ID (null for new conversation)
 * @param content - The user message content
 * @param callbacks - Callbacks for handling SSE events
 * @returns AbortController for cancellation
 */
export async function streamChatMessage(
  conversationId: string | null,
  content: string,
  callbacks: ChatStreamCallbacks
): Promise<AbortController> {
  const abortController = new AbortController();
  const API_BASE_URL = getApiBaseUrl();

  // Build endpoint URL
  const endpoint = conversationId
    ? `/api/v1/chat/conversations/${conversationId}/stream`
    : '/api/v1/chat/stream';

  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ content }),
      signal: abortController.signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorDetail = `HTTP ${response.status}: ${response.statusText}`;

      try {
        const errorJson = JSON.parse(errorText);
        errorDetail = errorJson.detail || errorDetail;
      } catch {
        // Use default error detail
      }

      callbacks.onError?.('http_error', errorDetail);
      return abortController;
    }

    if (!response.body) {
      callbacks.onError?.('no_body', 'No response body');
      return abortController;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    // Process the SSE stream
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages (delimiter is \n\n)
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
          const event = JSON.parse(jsonStr) as ChatSseEvent;
          handleSseEvent(event, callbacks);

          // Terminal events
          if (event.event === 'done' || event.event === 'error') {
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

    callbacks.onError?.(
      'stream_error',
      (err as Error).message || 'Stream request failed'
    );
  }

  return abortController;
}

/**
 * Handle individual SSE events and dispatch to appropriate callbacks.
 */
function handleSseEvent(
  event: ChatSseEvent,
  callbacks: ChatStreamCallbacks
): void {
  const messageId = event.message_id || '';

  switch (event.event) {
    case 'status': {
      const status = (event.data.status as string) || '';
      const detail = event.data.detail as string | undefined;
      callbacks.onStatus?.(status, detail);
      break;
    }

    case 'message.delta': {
      const delta = (event.data.delta as string) || '';
      callbacks.onDelta?.(delta, messageId);
      break;
    }

    case 'blocks.append': {
      const blocks = (event.data.blocks as ChatContentBlock[]) || [];
      callbacks.onBlocksAppend?.(blocks, messageId);
      break;
    }

    case 'message.complete': {
      callbacks.onComplete?.(messageId);
      break;
    }

    case 'error': {
      const errorCode = (event.data.error_code as string) || 'unknown';
      const detail = (event.data.detail as string) || 'Unknown error';
      callbacks.onError?.(errorCode, detail);
      break;
    }

    case 'done': {
      callbacks.onDone?.();
      break;
    }

    case 'tool.started': {
      const toolName = (event.data.tool_name as string) || '';
      callbacks.onToolStarted?.(toolName, event.data);
      break;
    }

    case 'tool.proposed': {
      const proposalId = (event.data.proposal_id as string) || '';
      callbacks.onToolProposed?.(proposalId, event.data);
      break;
    }

    case 'tool.result': {
      callbacks.onToolResult?.(event.data);
      break;
    }

    case 'tool.canceled':
    case 'memory.updated':
    case 'summary.updated':
      // These events are logged but not yet handled by UI
      logger.debug(`Chat SSE event: ${event.event}`, event.data);
      break;

    default:
      logger.warn(`Unknown chat SSE event type: ${event.event}`);
  }
}

// -----------------------------------------------------------------------------
// Conversation History API
// -----------------------------------------------------------------------------

/**
 * Fetch the list of conversations for the current user.
 *
 * @param limit - Maximum number of conversations to return (default 20)
 * @param offset - Offset for pagination (default 0)
 * @returns Paginated conversation list
 */
export async function fetchConversations(
  limit = 20,
  offset = 0
): Promise<ConversationListResponse> {
  const API_BASE_URL = getApiBaseUrl();
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  const url = `${API_BASE_URL}/api/v1/chat/conversations?${params.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;

    try {
      const errorJson = JSON.parse(errorText);
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // Use default error detail
    }

    throw new ApiErrorImpl(errorDetail, response.status, 'http_error');
  }

  return response.json();
}

/**
 * Fetch message history for a specific conversation.
 *
 * @param conversationId - The conversation ID
 * @param limit - Maximum number of messages to return (default 50)
 * @param beforeId - Optional cursor for pagination (fetch messages before this ID)
 * @returns Paginated message history
 */
export async function fetchMessages(
  conversationId: string,
  limit = 50,
  beforeId?: string
): Promise<MessageHistoryResponse> {
  const API_BASE_URL = getApiBaseUrl();
  const params = new URLSearchParams({
    limit: limit.toString(),
  });

  if (beforeId) {
    params.append('before_id', beforeId);
  }

  const url = `${API_BASE_URL}/api/v1/chat/conversations/${conversationId}/messages?${params.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;

    try {
      const errorJson = JSON.parse(errorText);
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // Use default error detail
    }

    throw new ApiErrorImpl(errorDetail, response.status, 'http_error');
  }

  return response.json();
}

// -----------------------------------------------------------------------------
// Action API
// -----------------------------------------------------------------------------

/**
 * Accept a proposed action.
 *
 * @param proposalId - The action proposal ID
 * @param confirmed - Whether the action is confirmed (default true)
 * @returns Action response with result
 */
export async function acceptAction(
  proposalId: string,
  confirmed = true
): Promise<{ success: boolean; action_id: string; status: string }> {
  const API_BASE_URL = getApiBaseUrl();
  const url = `${API_BASE_URL}/api/v1/chat/actions/${proposalId}/accept`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ confirmed }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;

    try {
      const errorJson = JSON.parse(errorText);
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // Use default error detail
    }

    throw new ApiErrorImpl(errorDetail, response.status, 'http_error');
  }

  return response.json();
}

/**
 * Cancel a proposed action.
 *
 * @param proposalId - The action proposal ID
 * @returns Action response
 */
export async function cancelAction(
  proposalId: string
): Promise<{ success: boolean; action_id: string; status: string }> {
  const API_BASE_URL = getApiBaseUrl();
  const url = `${API_BASE_URL}/api/v1/chat/actions/${proposalId}/cancel`;

  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;

    try {
      const errorJson = JSON.parse(errorText);
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // Use default error detail
    }

    throw new ApiErrorImpl(errorDetail, response.status, 'http_error');
  }

  return response.json();
}
