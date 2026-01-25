import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { useChatStore } from '../useChatStore';

// Mock the chat API endpoints
vi.mock('../../api/endpoints/chat', () => ({
  fetchConversations: vi.fn(),
  fetchMessages: vi.fn(),
  streamChatMessage: vi.fn(),
  acceptAction: vi.fn(),
  cancelAction: vi.fn(),
  deleteConversation: vi.fn(),
}));

// Mock logger to avoid console noise
vi.mock('../../lib/logger', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
  },
}));

// Get the mocked functions
const getMocks = async () => {
  const chatApi = await import('../../api/endpoints/chat');
  return {
    fetchConversations: chatApi.fetchConversations as ReturnType<typeof vi.fn>,
    fetchMessages: chatApi.fetchMessages as ReturnType<typeof vi.fn>,
    streamChatMessage: chatApi.streamChatMessage as ReturnType<typeof vi.fn>,
    acceptAction: chatApi.acceptAction as ReturnType<typeof vi.fn>,
    cancelAction: chatApi.cancelAction as ReturnType<typeof vi.fn>,
    deleteConversation: chatApi.deleteConversation as ReturnType<typeof vi.fn>,
  };
};

describe('useChatStore', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();

    act(() => {
      useChatStore.setState({
        hasHydrated: true,
        conversations: [],
        activeConversationId: null,
        messagesByConversationId: {},
        isLoading: false,
        isStreaming: false,
        streamingMessageId: null,
        error: null,
        _abortController: null,
      });
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  test('initializes with empty conversations', () => {
    const { result } = renderHook(() => useChatStore());

    expect(result.current.conversations).toEqual([]);
    expect(result.current.activeConversationId).toBeNull();
    expect(result.current.messagesByConversationId).toEqual({});
  });

  test('createConversation adds a new conversation and selects it', async () => {
    const { result } = renderHook(() => useChatStore());

    await act(async () => {
      await result.current.createConversation('My Chat');
    });

    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.conversations[0]?.title).toBe('My Chat');
    expect(result.current.activeConversationId).toBe(
      result.current.conversations[0]?.id
    );
    expect(
      result.current.messagesByConversationId[
        result.current.conversations[0]!.id
      ]
    ).toEqual([]);
  });

  test('switchConversation updates activeConversationId', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    // Mock empty messages response
    mocks.fetchMessages.mockResolvedValue({ messages: [], has_more: false });

    await act(async () => {
      await result.current.createConversation('Chat 1');
    });

    const convoId = result.current.conversations[0]!.id;

    await act(async () => {
      await result.current.switchConversation(convoId);
    });

    expect(result.current.activeConversationId).toBe(convoId);
  });

  test('loadConversations fetches from API and updates state', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    mocks.fetchConversations.mockResolvedValue({
      conversations: [
        {
          id: 'conv-1',
          title: 'Test Chat',
          created_at: '2026-01-17T10:00:00Z',
          last_activity_at: '2026-01-17T11:00:00Z',
        },
      ],
      total: 1,
      has_more: false,
    });

    await act(async () => {
      await result.current.loadConversations();
    });

    expect(useChatStore.getState().isLoading).toBe(false);
    expect(useChatStore.getState().conversations).toHaveLength(1);
    expect(useChatStore.getState().conversations[0]?.id).toBe('conv-1');
  });

  test('sendMessage creates a conversation if none exists and sends to API', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    // Mock streaming to immediately call onDone
    mocks.streamChatMessage.mockImplementation(
      async (_conversationId, _content, callbacks) => {
        // Simulate immediate completion
        callbacks.onDone?.();
        return new AbortController();
      }
    );

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    const conversationId = useChatStore.getState().activeConversationId;
    expect(conversationId).not.toBeNull();

    // Should have user message and streaming assistant placeholder
    const messages =
      useChatStore.getState().messagesByConversationId[conversationId!];
    expect(messages).toHaveLength(2);
    expect(messages?.[0]?.role).toBe('user');
    expect(messages?.[0]?.content).toBe('Hello');
    expect(messages?.[1]?.role).toBe('assistant');
  });

  test('sendMessage ignores empty/whitespace input', async () => {
    const { result } = renderHook(() => useChatStore());

    await act(async () => {
      await result.current.sendMessage('   ');
    });

    expect(useChatStore.getState().conversations).toHaveLength(0);
  });

  test('cancelPendingAssistantReply aborts the stream and clears streaming state', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    const mockAbortController = new AbortController();

    // Mock streaming that doesn't immediately complete
    mocks.streamChatMessage.mockImplementation(async () => {
      return mockAbortController;
    });

    await act(async () => {
      await result.current.createConversation('Chat');
      await result.current.sendMessage('Hello');
    });

    // Manually set the abort controller as it would be after streamChatMessage
    act(() => {
      useChatStore.setState({
        isStreaming: true,
        _abortController: mockAbortController,
      });
    });

    expect(useChatStore.getState().isStreaming).toBe(true);

    act(() => {
      result.current.cancelPendingAssistantReply();
    });

    expect(useChatStore.getState().isLoading).toBe(false);
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  test('clearConversation clears messages for the given conversation', async () => {
    const { result } = renderHook(() => useChatStore());

    await act(async () => {
      await result.current.createConversation('Chat');
    });

    const conversationId = useChatStore.getState().activeConversationId!;

    // Add a message directly to state
    act(() => {
      useChatStore.setState({
        messagesByConversationId: {
          [conversationId]: [
            {
              id: 'msg-1',
              conversationId,
              role: 'user',
              content: 'Hello',
              createdAt: new Date().toISOString(),
            },
          ],
        },
      });
    });

    expect(
      useChatStore.getState().messagesByConversationId[conversationId]
    ).toHaveLength(1);

    act(() => {
      result.current.clearConversation(conversationId);
    });

    expect(
      useChatStore.getState().messagesByConversationId[conversationId]
    ).toEqual([]);
  });

  test('acceptAction calls API', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    mocks.acceptAction.mockResolvedValue({
      success: true,
      action_id: 'action-1',
      status: 'accepted',
    });

    await act(async () => {
      await result.current.acceptAction('action-1');
    });

    expect(mocks.acceptAction).toHaveBeenCalledWith('action-1');
  });

  test('cancelAction calls API', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    mocks.cancelAction.mockResolvedValue({
      success: true,
      action_id: 'action-1',
      status: 'canceled',
    });

    await act(async () => {
      await result.current.cancelAction('action-1');
    });

    expect(mocks.cancelAction).toHaveBeenCalledWith('action-1');
  });

  test('deleteConversation removes conversation from state', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    // Create two conversations
    await act(async () => {
      await result.current.createConversation('Chat 1');
    });
    const conv1Id = result.current.conversations[0]!.id;

    await act(async () => {
      await result.current.createConversation('Chat 2');
    });
    const conv2Id = result.current.conversations[0]!.id;

    // Conversations are added to beginning, so order is [Chat 2, Chat 1]
    expect(result.current.conversations).toHaveLength(2);
    expect(result.current.conversations[0]!.id).toBe(conv2Id);
    expect(result.current.conversations[1]!.id).toBe(conv1Id);

    // Mock successful API deletion
    mocks.deleteConversation.mockResolvedValue(undefined);

    // Delete the first conversation (Chat 1)
    await act(async () => {
      await result.current.deleteConversation(conv1Id);
    });

    // Verify conversation was removed
    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.conversations[0]!.id).toBe(conv2Id);
    expect(result.current.messagesByConversationId[conv1Id]).toBeUndefined();
    expect(mocks.deleteConversation).toHaveBeenCalledWith(conv1Id);
  });

  test('deleteConversation switches to another conversation when deleting active one', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    // Create two conversations
    await act(async () => {
      await result.current.createConversation('Chat 1');
    });
    const conv1Id = result.current.conversations[0]!.id;

    await act(async () => {
      await result.current.createConversation('Chat 2');
    });
    const conv2Id = result.current.conversations[0]!.id;

    // Conversations are added to beginning, so order is [Chat 2, Chat 1]
    // Chat 2 is the active one after creation
    expect(result.current.activeConversationId).toBe(conv2Id);

    // Mock successful API deletion
    mocks.deleteConversation.mockResolvedValue(undefined);

    // Delete the active conversation (Chat 2)
    await act(async () => {
      await result.current.deleteConversation(conv2Id);
    });

    // Should switch to the remaining conversation (Chat 1)
    expect(result.current.activeConversationId).toBe(conv1Id);
  });

  test('deleteConversation creates new conversation when deleting the last one', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    // Create one conversation
    await act(async () => {
      await result.current.createConversation('Last Chat');
    });
    const convId = result.current.conversations[0]!.id;

    expect(result.current.conversations).toHaveLength(1);

    // Mock successful API deletion
    mocks.deleteConversation.mockResolvedValue(undefined);

    // Delete the only conversation
    await act(async () => {
      await result.current.deleteConversation(convId);
    });

    // Should have created a new conversation automatically
    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.conversations[0]!.id).not.toBe(convId);
    // Title should be a formatted date string instead of 'Chat with Nibble'
    expect(result.current.conversations[0]!.title).toMatch(
      /^\w{3} \d{1,2}, \d{4}, \d{1,2}:\d{2} (AM|PM)$/
    );
  });

  test('deleteConversation handles API errors', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    // Create a conversation
    await act(async () => {
      await result.current.createConversation('Chat 1');
    });
    const convId = result.current.conversations[0]!.id;

    // Mock API error
    mocks.deleteConversation.mockRejectedValue(new Error('API error'));

    // Try to delete conversation
    await act(async () => {
      try {
        await result.current.deleteConversation(convId);
      } catch (e) {
        // Expected to throw
      }
    });

    // Conversation should still be there since deletion failed
    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.conversations[0]!.id).toBe(convId);
    expect(result.current.error).toBe('Failed to delete conversation');
  });
});
