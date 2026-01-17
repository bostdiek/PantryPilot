import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock logger
vi.mock('../../../lib/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

// Mock api client
vi.mock('../../client', () => ({
  apiClient: { request: vi.fn() },
  getApiBaseUrl: () => 'http://api',
}));

// Control auth token in tests
let tokenValue: string | null = 'test-token';
vi.mock('../../../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: () => ({ token: tokenValue }),
  },
}));

import { ApiErrorImpl } from '../../../types/api';
import {
  acceptAction,
  cancelAction,
  fetchConversations,
  fetchMessages,
  streamChatMessage,
} from '../chat';

describe('chat API endpoints', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    tokenValue = 'test-token';
  });

  // ---------------------------------------------------------------------------
  // streamChatMessage
  // ---------------------------------------------------------------------------

  describe('streamChatMessage', () => {
    it('sends POST to correct endpoint for new conversation', async () => {
      const callbacks = {
        onDone: vi.fn(),
      };

      // Prepare a fake reader that returns one done event
      const encoder = new TextEncoder();
      const doneEvent = {
        event: 'done',
        conversation_id: 'conv-123',
        message_id: null,
        data: {},
      };
      const sse = 'data: ' + JSON.stringify(doneEvent) + '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      const fakeBody = { getReader: () => reader };

      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true, body: fakeBody });

      const abortController = await streamChatMessage(null, 'Hello', callbacks);

      expect(abortController).toBeDefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://api/api/v1/chat/stream',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          }),
          body: JSON.stringify({ content: 'Hello' }),
        })
      );
      expect(callbacks.onDone).toHaveBeenCalled();
    });

    it('sends POST to correct endpoint for existing conversation', async () => {
      const callbacks = { onDone: vi.fn() };

      const encoder = new TextEncoder();
      const doneEvent = {
        event: 'done',
        conversation_id: 'conv-456',
        message_id: null,
        data: {},
      };
      const sse = 'data: ' + JSON.stringify(doneEvent) + '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: { getReader: () => reader },
      });

      await streamChatMessage('conv-456', 'Hello', callbacks);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://api/api/v1/chat/conversations/conv-456/stream',
        expect.anything()
      );
    });

    it('calls onStatus callback for status events', async () => {
      const callbacks = {
        onStatus: vi.fn(),
        onDone: vi.fn(),
      };

      const encoder = new TextEncoder();
      const statusEvent = {
        event: 'status',
        conversation_id: 'conv-123',
        message_id: null,
        data: { status: 'thinking', detail: 'Processing your request' },
      };
      const doneEvent = {
        event: 'done',
        conversation_id: 'conv-123',
        message_id: null,
        data: {},
      };
      const sse =
        'data: ' +
        JSON.stringify(statusEvent) +
        '\n\n' +
        'data: ' +
        JSON.stringify(doneEvent) +
        '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: { getReader: () => reader },
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onStatus).toHaveBeenCalledWith(
        'thinking',
        'Processing your request'
      );
    });

    it('calls onDelta callback for message.delta events', async () => {
      const callbacks = {
        onDelta: vi.fn(),
        onDone: vi.fn(),
      };

      const encoder = new TextEncoder();
      const deltaEvent = {
        event: 'message.delta',
        conversation_id: 'conv-123',
        message_id: 'msg-123',
        data: { delta: 'Hello ' },
      };
      const doneEvent = {
        event: 'done',
        conversation_id: 'conv-123',
        message_id: null,
        data: {},
      };
      const sse =
        'data: ' +
        JSON.stringify(deltaEvent) +
        '\n\n' +
        'data: ' +
        JSON.stringify(doneEvent) +
        '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: { getReader: () => reader },
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onDelta).toHaveBeenCalledWith('Hello ', 'msg-123');
    });

    it('calls onBlocksAppend callback for blocks.append events', async () => {
      const callbacks = {
        onBlocksAppend: vi.fn(),
        onDone: vi.fn(),
      };

      const blocks = [{ type: 'text', text: 'Hello world!' }];
      const encoder = new TextEncoder();
      const blocksEvent = {
        event: 'blocks.append',
        conversation_id: 'conv-123',
        message_id: 'msg-123',
        data: { blocks },
      };
      const doneEvent = {
        event: 'done',
        conversation_id: 'conv-123',
        message_id: null,
        data: {},
      };
      const sse =
        'data: ' +
        JSON.stringify(blocksEvent) +
        '\n\n' +
        'data: ' +
        JSON.stringify(doneEvent) +
        '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: { getReader: () => reader },
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onBlocksAppend).toHaveBeenCalledWith(blocks, 'msg-123');
    });

    it('calls onComplete callback for message.complete events', async () => {
      const callbacks = {
        onComplete: vi.fn(),
        onDone: vi.fn(),
      };

      const encoder = new TextEncoder();
      const completeEvent = {
        event: 'message.complete',
        conversation_id: 'conv-123',
        message_id: 'msg-123',
        data: {},
      };
      const doneEvent = {
        event: 'done',
        conversation_id: 'conv-123',
        message_id: null,
        data: {},
      };
      const sse =
        'data: ' +
        JSON.stringify(completeEvent) +
        '\n\n' +
        'data: ' +
        JSON.stringify(doneEvent) +
        '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: { getReader: () => reader },
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onComplete).toHaveBeenCalledWith('msg-123');
    });

    it('calls onError callback for error events from SSE', async () => {
      const callbacks = {
        onError: vi.fn(),
      };

      const encoder = new TextEncoder();
      const errorEvent = {
        event: 'error',
        conversation_id: 'conv-123',
        message_id: null,
        data: { error_code: 'rate_limit', detail: 'Too many requests' },
      };
      const sse = 'data: ' + JSON.stringify(errorEvent) + '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: { getReader: () => reader },
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onError).toHaveBeenCalledWith(
        'rate_limit',
        'Too many requests'
      );
    });

    it('calls onToolStarted callback for tool.started events', async () => {
      const callbacks = {
        onToolStarted: vi.fn(),
        onDone: vi.fn(),
      };

      const encoder = new TextEncoder();
      const toolEvent = {
        event: 'tool.started',
        conversation_id: 'conv-123',
        message_id: 'msg-123',
        data: { tool_name: 'search_recipes', query: 'pasta' },
      };
      const doneEvent = {
        event: 'done',
        conversation_id: 'conv-123',
        message_id: null,
        data: {},
      };
      const sse =
        'data: ' +
        JSON.stringify(toolEvent) +
        '\n\n' +
        'data: ' +
        JSON.stringify(doneEvent) +
        '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: { getReader: () => reader },
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onToolStarted).toHaveBeenCalledWith('search_recipes', {
        tool_name: 'search_recipes',
        query: 'pasta',
      });
    });

    it('calls onToolProposed callback for tool.proposed events', async () => {
      const callbacks = {
        onToolProposed: vi.fn(),
        onDone: vi.fn(),
      };

      const encoder = new TextEncoder();
      const proposedEvent = {
        event: 'tool.proposed',
        conversation_id: 'conv-123',
        message_id: 'msg-123',
        data: { proposal_id: 'prop-123', action: 'add_to_meal_plan' },
      };
      const doneEvent = {
        event: 'done',
        conversation_id: 'conv-123',
        message_id: null,
        data: {},
      };
      const sse =
        'data: ' +
        JSON.stringify(proposedEvent) +
        '\n\n' +
        'data: ' +
        JSON.stringify(doneEvent) +
        '\n\n';
      const chunk = encoder.encode(sse);

      let readCalls = 0;
      const reader = {
        read: async () => {
          readCalls += 1;
          if (readCalls === 1) return { value: chunk, done: false };
          return { value: undefined, done: true };
        },
        cancel: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: { getReader: () => reader },
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onToolProposed).toHaveBeenCalledWith('prop-123', {
        proposal_id: 'prop-123',
        action: 'add_to_meal_plan',
      });
    });

    it('handles HTTP error response', async () => {
      const callbacks = {
        onError: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        text: vi
          .fn()
          .mockResolvedValue(JSON.stringify({ detail: 'Invalid token' })),
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onError).toHaveBeenCalledWith(
        'http_error',
        'Invalid token'
      );
    });

    it('handles no response body', async () => {
      const callbacks = {
        onError: vi.fn(),
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        body: null,
      });

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onError).toHaveBeenCalledWith(
        'no_body',
        'No response body'
      );
    });

    it('does not call onError for AbortError', async () => {
      const callbacks = {
        onError: vi.fn(),
      };

      const abortErr = new Error('aborted');
      abortErr.name = 'AbortError';
      global.fetch = vi.fn().mockRejectedValueOnce(abortErr);

      const abortController = await streamChatMessage(null, 'Hello', callbacks);

      expect(abortController).toBeDefined();
      expect(callbacks.onError).not.toHaveBeenCalled();
    });

    it('calls onError for stream errors', async () => {
      const callbacks = {
        onError: vi.fn(),
      };

      global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));

      await streamChatMessage(null, 'Hello', callbacks);

      expect(callbacks.onError).toHaveBeenCalledWith(
        'stream_error',
        'Network error'
      );
    });
  });

  // ---------------------------------------------------------------------------
  // fetchConversations
  // ---------------------------------------------------------------------------

  describe('fetchConversations', () => {
    it('fetches conversations with default pagination', async () => {
      const mockResponse = {
        conversations: [
          {
            id: 'conv-1',
            title: 'Test conversation',
            created_at: '2026-01-17T10:00:00Z',
            last_activity_at: '2026-01-17T11:00:00Z',
          },
        ],
        total: 1,
        has_more: false,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      const result = await fetchConversations();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://api/api/v1/chat/conversations?limit=20&offset=0',
        expect.objectContaining({
          method: 'GET',
          headers: { Authorization: 'Bearer test-token' },
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('fetches conversations with custom pagination', async () => {
      const mockResponse = {
        conversations: [],
        total: 50,
        has_more: true,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      await fetchConversations(10, 20);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://api/api/v1/chat/conversations?limit=10&offset=20',
        expect.anything()
      );
    });

    it('throws ApiErrorImpl on HTTP error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Server Error',
        text: vi.fn().mockResolvedValue(JSON.stringify({ detail: 'DB error' })),
      });

      await expect(fetchConversations()).rejects.toThrow(ApiErrorImpl);

      await expect(fetchConversations()).rejects.toMatchObject({
        status: 500,
        message: 'DB error',
      });
    });
  });

  // ---------------------------------------------------------------------------
  // fetchMessages
  // ---------------------------------------------------------------------------

  describe('fetchMessages', () => {
    it('fetches messages with default limit', async () => {
      const mockResponse = {
        messages: [
          {
            id: 'msg-1',
            role: 'user',
            content_blocks: [{ type: 'text', text: 'Hello' }],
            created_at: '2026-01-17T10:00:00Z',
          },
        ],
        has_more: false,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      const result = await fetchMessages('conv-123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://api/api/v1/chat/conversations/conv-123/messages?limit=50',
        expect.objectContaining({
          method: 'GET',
          headers: { Authorization: 'Bearer test-token' },
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('fetches messages with beforeId cursor', async () => {
      const mockResponse = {
        messages: [],
        has_more: false,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      await fetchMessages('conv-123', 25, 'msg-50');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://api/api/v1/chat/conversations/conv-123/messages?limit=25&before_id=msg-50',
        expect.anything()
      );
    });

    it('throws ApiErrorImpl on HTTP error', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: vi
          .fn()
          .mockResolvedValue(
            JSON.stringify({ detail: 'Conversation not found' })
          ),
      });

      await expect(fetchMessages('conv-not-exist')).rejects.toThrow(
        ApiErrorImpl
      );
    });
  });

  // ---------------------------------------------------------------------------
  // acceptAction
  // ---------------------------------------------------------------------------

  describe('acceptAction', () => {
    it('sends POST to accept endpoint with confirmation', async () => {
      const mockResponse = {
        success: true,
        action_id: 'action-123',
        status: 'accepted',
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      const result = await acceptAction('prop-123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://api/api/v1/chat/actions/prop-123/accept',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          }),
          body: JSON.stringify({ confirmed: true }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('sends confirmation: false when specified', async () => {
      const mockResponse = {
        success: true,
        action_id: 'action-123',
        status: 'pending',
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      await acceptAction('prop-123', false);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          body: JSON.stringify({ confirmed: false }),
        })
      );
    });

    it('throws ApiErrorImpl on HTTP error', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: vi
          .fn()
          .mockResolvedValue(JSON.stringify({ detail: 'Action expired' })),
      });

      await expect(acceptAction('prop-expired')).rejects.toThrow(ApiErrorImpl);
    });
  });

  // ---------------------------------------------------------------------------
  // cancelAction
  // ---------------------------------------------------------------------------

  describe('cancelAction', () => {
    it('sends POST to cancel endpoint', async () => {
      const mockResponse = {
        success: true,
        action_id: 'action-123',
        status: 'canceled',
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      const result = await cancelAction('prop-123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://api/api/v1/chat/actions/prop-123/cancel',
        expect.objectContaining({
          method: 'POST',
          headers: { Authorization: 'Bearer test-token' },
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('throws ApiErrorImpl on HTTP error', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: vi
          .fn()
          .mockResolvedValue(JSON.stringify({ detail: 'Action not found' })),
      });

      await expect(cancelAction('prop-not-exist')).rejects.toThrow(
        ApiErrorImpl
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Auth header handling
  // ---------------------------------------------------------------------------

  describe('auth header handling', () => {
    it('does not include auth header when no token', async () => {
      tokenValue = null;

      const mockResponse = {
        conversations: [],
        total: 0,
        has_more: false,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      await fetchConversations();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          headers: {},
        })
      );
    });
  });
});
