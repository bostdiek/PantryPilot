import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { ApiErrorImpl } from '../../types/api';
import { useChatStore } from '../useChatStore';

// Mock the chat API endpoints
vi.mock('../../api/endpoints/chat', () => ({
  fetchConversations: vi.fn(),
  fetchMessages: vi.fn(),
  resumeRecipeConversation: vi.fn(),
  createRecipeConversation: vi.fn(),
  selectRecipeConversation: vi.fn(),
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
vi.mock('../../lib/telemetry', () => ({
  createProductTelemetryRequestMetadata: vi.fn((input) => ({
    requestId: 'store-req-id',
    featureName: input.featureName,
    conversationId: input.conversationId,
  })),
  emitProductTelemetryEvent: vi.fn(),
  getTelemetryLatencyMs: vi.fn(() => 10),
  classifyTelemetryError: vi.fn(() => 'mock_error'),
}));

// Get the mocked functions
const getMocks = async () => {
  const chatApi = await import('../../api/endpoints/chat');
  return {
    fetchConversations: chatApi.fetchConversations as ReturnType<typeof vi.fn>,
    fetchMessages: chatApi.fetchMessages as ReturnType<typeof vi.fn>,
    resumeRecipeConversation: chatApi.resumeRecipeConversation as ReturnType<
      typeof vi.fn
    >,
    createRecipeConversation: chatApi.createRecipeConversation as ReturnType<
      typeof vi.fn
    >,
    selectRecipeConversation: chatApi.selectRecipeConversation as ReturnType<
      typeof vi.fn
    >,
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
        activeGeneralConversationId: null,
        activeRecipeConversationIds: {},
        messagesByConversationId: {},
        hasPreviousMessagesByConversationId: {},
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
    expect(result.current.conversations[0]?.recipeContext).toBeUndefined();
    expect(result.current.activeGeneralConversationId).toBe(
      result.current.conversations[0]?.id
    );
  });

  test('resumeRecipeConversation always reconciles with the server and deduplicates its summary', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'persisted-context',
            title: 'Persisted',
            createdAt: '2026-09-01T10:00:00Z',
            lastMessageAt: '2026-09-01T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
        ],
        activeConversationId: 'persisted-context',
        activeRecipeConversationIds: {
          'recipe-1': 'persisted-context',
        },
      });
    });
    mocks.resumeRecipeConversation.mockResolvedValue({
      id: 'server-context',
      title: 'Server current',
      created_at: '2026-09-02T10:00:00Z',
      last_activity_at: '2026-09-02T11:00:00Z',
      recipe_context: {
        recipe_id: 'recipe-1',
        recipe_title: 'Pasta',
        is_current: true,
      },
    });
    mocks.fetchMessages.mockResolvedValue({ messages: [], has_more: false });

    await act(async () => {
      await result.current.resumeRecipeConversation('recipe-1');
      await result.current.resumeRecipeConversation('recipe-1');
    });

    expect(mocks.resumeRecipeConversation).toHaveBeenCalledTimes(2);
    expect(result.current.activeConversationId).toBe('server-context');
    expect(result.current.activeRecipeConversationIds['recipe-1']).toBe(
      'server-context'
    );
    expect(
      result.current.conversations.filter(
        (conversation) => conversation.id === 'server-context'
      )
    ).toHaveLength(1);
    expect(
      result.current.conversations.find(
        (conversation) => conversation.id === 'persisted-context'
      )?.recipeContext?.isCurrent
    ).toBe(false);
  });

  test('loadConversations reconciles independent current selections for each recipe', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    act(() => {
      useChatStore.setState({
        activeConversationId: 'removed-context',
        activeGeneralConversationId: 'removed-general',
        activeRecipeConversationIds: {
          'recipe-1': 'stale-recipe-1',
          'removed-recipe': 'removed-context',
        },
      });
    });
    mocks.fetchConversations.mockResolvedValue({
      conversations: [
        {
          id: 'general',
          title: 'General',
          created_at: '2026-09-29T08:00:00Z',
          last_activity_at: '2026-09-29T08:00:00Z',
          recipe_context: null,
        },
        {
          id: 'recipe-1-current',
          title: 'Pasta',
          created_at: '2026-09-29T09:00:00Z',
          last_activity_at: '2026-09-29T09:00:00Z',
          recipe_context: {
            recipe_id: 'recipe-1',
            recipe_title: 'Pasta',
            is_current: true,
          },
        },
        {
          id: 'recipe-1-older',
          title: 'Older pasta',
          created_at: '2026-09-28T09:00:00Z',
          last_activity_at: '2026-09-28T09:00:00Z',
          recipe_context: {
            recipe_id: 'recipe-1',
            recipe_title: 'Pasta',
            is_current: false,
          },
        },
        {
          id: 'recipe-2-current',
          title: 'Soup',
          created_at: '2026-09-29T10:00:00Z',
          last_activity_at: '2026-09-29T10:00:00Z',
          recipe_context: {
            recipe_id: 'recipe-2',
            recipe_title: 'Soup',
            is_current: true,
          },
        },
      ],
      total: 4,
      has_more: false,
    });

    await act(async () => {
      await result.current.loadConversations();
    });

    expect(result.current.activeRecipeConversationIds).toEqual({
      'recipe-1': 'recipe-1-current',
      'recipe-2': 'recipe-2-current',
    });
    expect(result.current.activeGeneralConversationId).toBeNull();
    expect(result.current.activeConversationId).toBeNull();
  });

  test('loadConversations preserves only the selected local-first general conversation', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    await act(async () => {
      await result.current.createConversation('Older local chat');
      await result.current.createConversation('Selected local chat');
    });
    const selectedLocalId = result.current.activeGeneralConversationId;
    mocks.fetchConversations.mockResolvedValue({
      conversations: [
        {
          id: 'recipe-current',
          title: 'Pasta',
          created_at: '2026-09-29T09:00:00Z',
          last_activity_at: '2026-09-29T09:00:00Z',
          recipe_context: {
            recipe_id: 'recipe-1',
            recipe_title: 'Pasta',
            is_current: true,
          },
        },
      ],
      total: 1,
      has_more: false,
    });

    await act(async () => {
      await result.current.loadConversations();
    });

    expect(result.current.activeConversationId).toBe(selectedLocalId);
    expect(result.current.activeGeneralConversationId).toBe(selectedLocalId);
    expect(
      result.current.conversations.find(
        (conversation) => conversation.id === selectedLocalId
      )
    ).toMatchObject({
      title: 'Selected local chat',
      isLocalOnly: true,
    });
    expect(
      result.current.conversations.some(
        (conversation) => conversation.title === 'Older local chat'
      )
    ).toBe(false);
    expect(result.current.activeRecipeConversationIds).toEqual({
      'recipe-1': 'recipe-current',
    });
  });

  test('createRecipeConversation persists a contextual thread without changing the general selection', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    await act(async () => {
      await result.current.createConversation('General');
    });
    const generalId = result.current.activeConversationId;
    mocks.createRecipeConversation.mockResolvedValue({
      id: 'context-new',
      title: null,
      created_at: '2026-09-02T10:00:00Z',
      last_activity_at: '2026-09-02T10:00:00Z',
      recipe_context: {
        recipe_id: 'recipe-1',
        recipe_title: 'Pasta',
        is_current: true,
      },
    });

    await act(async () => {
      await result.current.createRecipeConversation('recipe-1');
    });

    expect(result.current.activeConversationId).toBe('context-new');
    expect(result.current.activeGeneralConversationId).toBe(generalId);
    expect(result.current.messagesByConversationId['context-new']).toEqual([]);
  });

  test('creates contextual threads per recipe without crossing selections', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    await act(async () => {
      await result.current.createConversation('General');
    });
    const generalId = result.current.activeGeneralConversationId;
    mocks.createRecipeConversation
      .mockResolvedValueOnce({
        id: 'recipe-1-context',
        title: 'Pasta',
        created_at: '2026-09-29T10:00:00Z',
        last_activity_at: '2026-09-29T10:00:00Z',
        recipe_context: {
          recipe_id: 'recipe-1',
          recipe_title: 'Pasta',
          is_current: true,
        },
      })
      .mockResolvedValueOnce({
        id: 'recipe-2-context',
        title: 'Soup',
        created_at: '2026-09-29T11:00:00Z',
        last_activity_at: '2026-09-29T11:00:00Z',
        recipe_context: {
          recipe_id: 'recipe-2',
          recipe_title: 'Soup',
          is_current: true,
        },
      });

    await act(async () => {
      await result.current.createRecipeConversation('recipe-1');
      await result.current.createRecipeConversation('recipe-2');
    });

    expect(mocks.createRecipeConversation.mock.calls).toEqual([
      ['recipe-1'],
      ['recipe-2'],
    ]);
    expect(result.current.activeRecipeConversationIds).toEqual({
      'recipe-1': 'recipe-1-context',
      'recipe-2': 'recipe-2-context',
    });
    expect(result.current.activeGeneralConversationId).toBe(generalId);
    expect(result.current.activeConversationId).toBe('recipe-2-context');
  });

  test('general New Chat stays context-free after a contextual selection', async () => {
    const { result } = renderHook(() => useChatStore());

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'recipe-context',
            title: 'Pasta',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
        ],
        activeConversationId: 'recipe-context',
        activeRecipeConversationIds: {
          'recipe-1': 'recipe-context',
        },
      });
    });

    await act(async () => {
      await result.current.createConversation('General after recipe');
    });

    const general = result.current.conversations[0];
    expect(general?.title).toBe('General after recipe');
    expect(general?.recipeContext).toBeUndefined();
    expect(result.current.activeGeneralConversationId).toBe(general?.id);
    expect(result.current.activeRecipeConversationIds).toEqual({
      'recipe-1': 'recipe-context',
    });
  });

  test('switchConversation selects contextual history before loading messages', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();
    const callOrder: string[] = [];

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'context-old',
            title: 'Older',
            createdAt: '2026-09-01T10:00:00Z',
            lastMessageAt: '2026-09-01T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: false,
            },
          },
        ],
      });
    });
    mocks.selectRecipeConversation.mockImplementation(async () => {
      callOrder.push('select');
      return {
        id: 'context-old',
        title: 'Older',
        created_at: '2026-09-01T10:00:00Z',
        last_activity_at: '2026-09-02T10:00:00Z',
        recipe_context: {
          recipe_id: 'recipe-1',
          recipe_title: 'Pasta',
          is_current: true,
        },
      };
    });
    mocks.fetchMessages.mockImplementation(async () => {
      callOrder.push('messages');
      return { messages: [], has_more: false };
    });

    await act(async () => {
      await result.current.switchConversation('context-old');
    });

    expect(callOrder).toEqual(['select', 'messages']);
    expect(result.current.activeConversationId).toBe('context-old');
    expect(result.current.conversations[0]?.recipeContext?.isCurrent).toBe(
      true
    );
  });

  test('removes inaccessible recipe state and surfaces an explicit error without general fallback', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'general',
            title: 'General',
            createdAt: '2026-09-01T09:00:00Z',
            lastMessageAt: '2026-09-01T09:00:00Z',
          },
          {
            id: 'stale-context',
            title: 'Stale',
            createdAt: '2026-09-01T10:00:00Z',
            lastMessageAt: '2026-09-01T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
        ],
        // A persisted general selection must not become a success-shaped
        // fallback when opening the recipe fails.
        activeConversationId: 'general',
        activeGeneralConversationId: 'general',
        activeRecipeConversationIds: { 'recipe-1': 'stale-context' },
        messagesByConversationId: {
          'stale-context': [
            {
              id: 'message-1',
              conversationId: 'stale-context',
              role: 'user',
              content: 'secret context',
              createdAt: '2026-09-01T10:01:00Z',
            },
          ],
        },
      });
    });
    mocks.resumeRecipeConversation.mockRejectedValue(
      new ApiErrorImpl('Forbidden', 403, 'http_error')
    );

    await act(async () => {
      await result.current.resumeRecipeConversation('recipe-1');
    });

    expect(result.current.activeConversationId).toBeNull();
    expect(result.current.activeGeneralConversationId).toBe('general');
    expect(result.current.conversations.map(({ id }) => id)).toEqual([
      'general',
    ]);
    expect(
      result.current.messagesByConversationId['stale-context']
    ).toBeUndefined();
    expect(
      result.current.activeRecipeConversationIds['recipe-1']
    ).toBeUndefined();
    expect(result.current.error).toContain('no longer available');
    expect(mocks.fetchMessages).not.toHaveBeenCalled();
  });

  test('cleans up confirmed inaccessible state for create and select failures', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();
    const seedRecipeState = () => {
      useChatStore.setState({
        conversations: [
          {
            id: 'recipe-context',
            title: 'Pasta',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
        ],
        activeConversationId: 'recipe-context',
        activeRecipeConversationIds: { 'recipe-1': 'recipe-context' },
        messagesByConversationId: { 'recipe-context': [] },
        error: null,
      });
    };

    act(seedRecipeState);
    mocks.createRecipeConversation.mockRejectedValueOnce(
      new ApiErrorImpl('Not found', 404, 'http_error')
    );
    await act(async () => {
      await result.current.createRecipeConversation('recipe-1');
    });
    expect(result.current.activeConversationId).toBeNull();
    expect(result.current.conversations).toEqual([]);
    expect(result.current.activeRecipeConversationIds).toEqual({});

    act(seedRecipeState);
    mocks.selectRecipeConversation.mockRejectedValueOnce(
      new ApiErrorImpl('Forbidden', 403, 'http_error')
    );
    await act(async () => {
      await result.current.switchConversation('recipe-context');
    });
    expect(result.current.activeConversationId).toBeNull();
    expect(result.current.conversations).toEqual([]);
    expect(result.current.activeRecipeConversationIds).toEqual({});
    expect(mocks.fetchMessages).not.toHaveBeenCalled();
  });

  test('recovers from an inaccessible recipe error on a later successful resume', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();
    mocks.resumeRecipeConversation
      .mockRejectedValueOnce(new ApiErrorImpl('Not found', 404, 'http_error'))
      .mockResolvedValueOnce({
        id: 'recipe-recovered',
        title: 'Recovered recipe chat',
        created_at: '2026-09-29T12:00:00Z',
        last_activity_at: '2026-09-29T12:00:00Z',
        recipe_context: {
          recipe_id: 'recipe-1',
          recipe_title: 'Pasta',
          is_current: true,
        },
      });
    mocks.fetchMessages.mockResolvedValue({ messages: [], has_more: false });

    await act(async () => {
      await result.current.resumeRecipeConversation('recipe-1');
    });
    expect(result.current.error).toContain('no longer available');
    expect(result.current.activeConversationId).toBeNull();

    await act(async () => {
      await result.current.resumeRecipeConversation('recipe-1');
    });

    expect(result.current.error).toBeNull();
    expect(result.current.activeConversationId).toBe('recipe-recovered');
    expect(result.current.activeRecipeConversationIds['recipe-1']).toBe(
      'recipe-recovered'
    );
    expect(mocks.fetchMessages).toHaveBeenCalledWith(
      'recipe-recovered',
      expect.any(Number)
    );
  });

  test('preserves recipe state and permits retry after a network resume failure', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();
    const conversation = {
      id: 'recipe-current',
      title: 'Pasta',
      createdAt: '2026-09-29T10:00:00Z',
      lastMessageAt: '2026-09-29T10:00:00Z',
      recipeContext: {
        recipeId: 'recipe-1',
        recipeTitle: 'Pasta',
        isCurrent: true,
      },
    };
    act(() => {
      useChatStore.setState({
        conversations: [conversation],
        activeConversationId: conversation.id,
        activeRecipeConversationIds: { 'recipe-1': conversation.id },
        messagesByConversationId: { [conversation.id]: [] },
      });
    });
    mocks.resumeRecipeConversation
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce({
        id: conversation.id,
        title: conversation.title,
        created_at: conversation.createdAt,
        last_activity_at: conversation.lastMessageAt,
        recipe_context: {
          recipe_id: 'recipe-1',
          recipe_title: 'Pasta',
          is_current: true,
        },
      });
    mocks.fetchMessages.mockResolvedValue({ messages: [], has_more: false });

    await act(async () => {
      await result.current.resumeRecipeConversation('recipe-1');
    });

    expect(result.current.activeConversationId).toBe(conversation.id);
    expect(result.current.activeRecipeConversationIds).toEqual({
      'recipe-1': conversation.id,
    });
    expect(result.current.conversations).toEqual([conversation]);
    expect(result.current.error).toContain('Please try again');

    await act(async () => {
      await result.current.resumeRecipeConversation('recipe-1');
    });
    expect(mocks.resumeRecipeConversation).toHaveBeenCalledTimes(2);
    expect(result.current.error).toBeNull();
  });

  test('preserves recipe state and permits retry after a 500 create failure', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();
    act(() => {
      useChatStore.setState({
        activeConversationId: 'recipe-current',
        activeRecipeConversationIds: { 'recipe-1': 'recipe-current' },
        conversations: [
          {
            id: 'recipe-current',
            title: 'Pasta',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
        ],
      });
    });
    mocks.createRecipeConversation
      .mockRejectedValueOnce(
        new ApiErrorImpl('Server error', 500, 'http_error')
      )
      .mockResolvedValueOnce({
        id: 'recipe-new',
        title: 'Pasta',
        created_at: '2026-09-29T11:00:00Z',
        last_activity_at: '2026-09-29T11:00:00Z',
        recipe_context: {
          recipe_id: 'recipe-1',
          recipe_title: 'Pasta',
          is_current: true,
        },
      });

    await act(async () => {
      await result.current.createRecipeConversation('recipe-1');
    });
    expect(result.current.activeConversationId).toBe('recipe-current');
    expect(result.current.activeRecipeConversationIds['recipe-1']).toBe(
      'recipe-current'
    );
    expect(result.current.error).toContain('Please try again');

    await act(async () => {
      await result.current.createRecipeConversation('recipe-1');
    });
    expect(mocks.createRecipeConversation).toHaveBeenCalledTimes(2);
    expect(result.current.activeConversationId).toBe('recipe-new');
    expect(result.current.error).toBeNull();
  });

  test('preserves recipe state and permits retry after a 500 select failure', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();
    act(() => {
      useChatStore.setState({
        activeConversationId: 'context-current',
        activeRecipeConversationIds: { 'recipe-1': 'context-current' },
        conversations: [
          {
            id: 'context-current',
            title: 'Current',
            createdAt: '2026-09-29T11:00:00Z',
            lastMessageAt: '2026-09-29T11:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
          {
            id: 'context-old',
            title: 'Older',
            createdAt: '2026-09-28T10:00:00Z',
            lastMessageAt: '2026-09-28T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: false,
            },
          },
        ],
      });
    });
    mocks.selectRecipeConversation
      .mockRejectedValueOnce(
        new ApiErrorImpl('Server error', 500, 'http_error')
      )
      .mockResolvedValueOnce({
        id: 'context-old',
        title: 'Older',
        created_at: '2026-09-28T10:00:00Z',
        last_activity_at: '2026-09-29T12:00:00Z',
        recipe_context: {
          recipe_id: 'recipe-1',
          recipe_title: 'Pasta',
          is_current: true,
        },
      });
    mocks.fetchMessages.mockResolvedValue({ messages: [], has_more: false });

    await act(async () => {
      await result.current.switchConversation('context-old');
    });
    expect(result.current.activeConversationId).toBe('context-current');
    expect(result.current.activeRecipeConversationIds['recipe-1']).toBe(
      'context-current'
    );
    expect(result.current.error).toContain('Please try again');

    await act(async () => {
      await result.current.switchConversation('context-old');
    });
    expect(mocks.selectRecipeConversation).toHaveBeenCalledTimes(2);
    expect(result.current.activeConversationId).toBe('context-old');
    expect(result.current.error).toBeNull();
  });

  test('rehydrates older persisted general conversations without recipe metadata', async () => {
    localStorage.setItem(
      'chat',
      JSON.stringify({
        state: {
          conversations: [
            {
              id: 'legacy-general',
              title: 'Legacy',
              createdAt: '2026-09-01T10:00:00Z',
              lastMessageAt: '2026-09-01T10:00:00Z',
            },
          ],
          activeConversationId: 'legacy-general',
          messagesByConversationId: {},
          hasPreviousMessagesByConversationId: {},
        },
        version: 0,
      })
    );

    await act(async () => {
      await useChatStore.persist.rehydrate();
    });

    expect(
      useChatStore.getState().conversations[0]?.recipeContext
    ).toBeUndefined();
    expect(useChatStore.getState().activeRecipeConversationIds).toEqual({});
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

  test('switchConversation always reloads messages from server even when cached', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    mocks.fetchMessages.mockResolvedValue({ messages: [], has_more: false });

    const convoId = 'cached-conv';

    // Pre-populate cache so the old skip-if-cached code would have returned early
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: convoId,
            title: 'Cached',
            createdAt: new Date().toISOString(),
            lastMessageAt: new Date().toISOString(),
          },
        ],
        messagesByConversationId: {
          [convoId]: [
            {
              id: 'm1',
              conversationId: convoId,
              role: 'user',
              content: 'cached message',
              createdAt: new Date().toISOString(),
            },
          ],
        },
      });
    });

    await act(async () => {
      await result.current.switchConversation(convoId);
    });

    // fetchMessages must be called even though the conversation had cached messages
    expect(mocks.fetchMessages).toHaveBeenCalledWith(convoId, 200);
  });

  test('loadMessages stores has_more=true in hasPreviousMessagesByConversationId', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    const conversationId = 'conv-paginated';
    mocks.fetchMessages.mockResolvedValue({
      messages: [
        {
          id: 'msg-1',
          role: 'user',
          content_blocks: [{ type: 'text', text: 'Hello' }],
          created_at: '2026-01-17T10:00:00Z',
        },
      ],
      has_more: true,
    });

    await act(async () => {
      await result.current.loadMessages(conversationId);
    });

    expect(
      useChatStore.getState().hasPreviousMessagesByConversationId[
        conversationId
      ]
    ).toBe(true);
  });

  test('loadMessages stores has_more=false in hasPreviousMessagesByConversationId', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    const conversationId = 'conv-complete';
    mocks.fetchMessages.mockResolvedValue({ messages: [], has_more: false });

    await act(async () => {
      await result.current.loadMessages(conversationId);
    });

    expect(
      useChatStore.getState().hasPreviousMessagesByConversationId[
        conversationId
      ]
    ).toBe(false);
  });

  test('loadMoreMessages fetches with the oldest message id as before_id cursor', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    const conversationId = 'conv-more';
    const oldestMsgId = 'msg-oldest';

    act(() => {
      useChatStore.setState({
        activeConversationId: conversationId,
        messagesByConversationId: {
          [conversationId]: [
            {
              id: oldestMsgId,
              conversationId,
              role: 'user',
              content: 'oldest',
              createdAt: '2026-01-17T10:00:00Z',
            },
            {
              id: 'msg-newer',
              conversationId,
              role: 'assistant',
              content: 'newer',
              createdAt: '2026-01-17T10:01:00Z',
            },
          ],
        },
        hasPreviousMessagesByConversationId: { [conversationId]: true },
      });
    });

    mocks.fetchMessages.mockResolvedValue({
      messages: [
        {
          id: 'msg-even-older',
          role: 'user',
          content_blocks: [{ type: 'text', text: 'Even older' }],
          created_at: '2026-01-17T09:59:00Z',
        },
      ],
      has_more: false,
    });

    await act(async () => {
      await result.current.loadMoreMessages(conversationId);
    });

    // Must pass the oldest message id as the cursor
    expect(mocks.fetchMessages).toHaveBeenCalledWith(
      conversationId,
      200,
      oldestMsgId
    );
  });

  test('loadMoreMessages prepends older messages before existing ones', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    const conversationId = 'conv-prepend';

    act(() => {
      useChatStore.setState({
        messagesByConversationId: {
          [conversationId]: [
            {
              id: 'msg-recent',
              conversationId,
              role: 'user',
              content: 'recent',
              createdAt: '2026-01-17T10:05:00Z',
            },
          ],
        },
        hasPreviousMessagesByConversationId: { [conversationId]: true },
      });
    });

    mocks.fetchMessages.mockResolvedValue({
      messages: [
        {
          id: 'msg-old-1',
          role: 'user',
          content_blocks: [{ type: 'text', text: 'Old 1' }],
          created_at: '2026-01-17T09:00:00Z',
        },
        {
          id: 'msg-old-2',
          role: 'assistant',
          content_blocks: [{ type: 'text', text: 'Old 2' }],
          created_at: '2026-01-17T09:30:00Z',
        },
      ],
      has_more: false,
    });

    await act(async () => {
      await result.current.loadMoreMessages(conversationId);
    });

    const messages =
      useChatStore.getState().messagesByConversationId[conversationId]!;

    // Older messages come first, then the existing recent message
    expect(messages).toHaveLength(3);
    expect(messages[0]?.id).toBe('msg-old-1');
    expect(messages[1]?.id).toBe('msg-old-2');
    expect(messages[2]?.id).toBe('msg-recent');

    // has_more updated to false now that we reached the beginning
    expect(
      useChatStore.getState().hasPreviousMessagesByConversationId[
        conversationId
      ]
    ).toBe(false);
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

  test('loadMessages extracts content from user message content_blocks', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    const conversationId = 'conv-1';

    // Mock API response with user and assistant messages
    mocks.fetchMessages.mockResolvedValue({
      messages: [
        {
          id: 'msg-1',
          role: 'user',
          content_blocks: [
            {
              type: 'text',
              text: 'Hello, how are you?',
            },
          ],
          created_at: '2026-01-17T10:00:00Z',
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content_blocks: [
            {
              type: 'text',
              text: 'I am doing well, thank you!',
            },
          ],
          created_at: '2026-01-17T10:01:00Z',
        },
        {
          id: 'msg-3',
          role: 'user',
          content_blocks: [
            {
              type: 'text',
              text: 'Can you help me with recipes?',
            },
          ],
          created_at: '2026-01-17T10:02:00Z',
        },
      ],
      has_more: false,
    });

    await act(async () => {
      await result.current.loadMessages(conversationId);
    });

    const messages =
      useChatStore.getState().messagesByConversationId[conversationId];

    expect(useChatStore.getState().isLoading).toBe(false);
    expect(messages).toHaveLength(3);

    // Verify user messages have content extracted from content_blocks
    expect(messages?.[0]?.role).toBe('user');
    expect(messages?.[0]?.content).toBe('Hello, how are you?');
    expect(messages?.[0]?.blocks).toBeDefined();

    // Verify assistant messages have blocks but no content field
    expect(messages?.[1]?.role).toBe('assistant');
    expect(messages?.[1]?.content).toBeUndefined();
    expect(messages?.[1]?.blocks).toHaveLength(1);
    expect(messages?.[1]?.blocks?.[0]?.type).toBe('text');

    // Verify second user message
    expect(messages?.[2]?.role).toBe('user');
    expect(messages?.[2]?.content).toBe('Can you help me with recipes?');
    expect(messages?.[2]?.blocks).toBeDefined();
  });

  test('sendMessage creates a conversation if none exists and sends to API', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    // Mock streaming to immediately call onDone
    mocks.streamChatMessage.mockImplementation(
      async (_conversationId, _content, callbacks) => {
        // Simulate immediate completion
        callbacks.onDone?.();
      }
    );

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    const conversationId = useChatStore.getState().activeConversationId;
    expect(conversationId).not.toBeNull();
    expect(mocks.streamChatMessage).toHaveBeenCalledWith(
      expect.any(String),
      'Hello',
      expect.any(Object),
      expect.anything(),
      expect.objectContaining({
        requestId: 'store-req-id',
        featureName: 'assistant',
      }),
      expect.any(AbortSignal)
    );

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

    // Mock streaming that doesn't immediately call callbacks (simulates in-flight stream)
    mocks.streamChatMessage.mockImplementation(async () => {
      // resolve without calling onDone so streaming state is preserved
    });

    await act(async () => {
      await result.current.createConversation('Chat');
      await result.current.sendMessage('Hello');
    });

    // The store sets _abortController and isStreaming=true before the stream starts.
    // Manually set isStreaming to simulate an ongoing stream (mock resolved without onDone).
    act(() => {
      useChatStore.setState({
        isStreaming: true,
      });
    });

    expect(useChatStore.getState().isStreaming).toBe(true);

    act(() => {
      result.current.cancelPendingAssistantReply();
    });

    expect(useChatStore.getState().isLoading).toBe(false);
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  test('sendMessage emits recipe_search_submitted when search tools start', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();
    const telemetry = await import('../../lib/telemetry');

    mocks.streamChatMessage.mockImplementation(
      async (_conversationId, _content, callbacks) => {
        callbacks.onToolStarted?.('search_recipes', {});
        callbacks.onDone?.();
      }
    );

    await act(async () => {
      await result.current.sendMessage('Find chicken recipes');
    });

    const emitSpy = telemetry.emitProductTelemetryEvent as ReturnType<
      typeof vi.fn
    >;
    expect(emitSpy).toHaveBeenCalledWith(
      'recipe_search_submitted',
      expect.any(Object),
      expect.objectContaining({
        tool_names: ['search_recipes'],
      })
    );
  });

  test.each([
    { status: 'success', errorCode: undefined, success: true },
    {
      status: 'error',
      errorCode: 'transient_database_error',
      success: false,
    },
  ])(
    'sendMessage records $status tool results accurately',
    async ({ status, errorCode, success }) => {
      const { result } = renderHook(() => useChatStore());
      const mocks = await getMocks();
      const telemetry = await import('../../lib/telemetry');

      mocks.streamChatMessage.mockImplementation(
        async (_conversationId, _content, callbacks) => {
          callbacks.onToolResult?.({
            tool_name: 'search_recipes',
            status,
            ...(errorCode ? { error_code: errorCode } : {}),
          });
          callbacks.onDone?.();
        }
      );

      await act(async () => {
        await result.current.sendMessage('Find recipes');
      });

      const emitSpy = telemetry.emitProductTelemetryEvent as ReturnType<
        typeof vi.fn
      >;
      expect(emitSpy).toHaveBeenCalledWith(
        'assistant_tool_completed',
        expect.any(Object),
        expect.objectContaining({
          success,
          error_type: errorCode,
          tool_names: ['search_recipes'],
          tool_count: 1,
        })
      );
    }
  );

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

  test('deleteConversation activates the server-promoted recipe conversation', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'recipe-current',
            title: 'Current',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
          {
            id: 'recipe-older',
            title: 'Older',
            createdAt: '2026-09-28T10:00:00Z',
            lastMessageAt: '2026-09-28T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: false,
            },
          },
          {
            id: 'general',
            title: 'General',
            createdAt: '2026-09-27T10:00:00Z',
            lastMessageAt: '2026-09-27T10:00:00Z',
          },
        ],
        activeConversationId: 'recipe-current',
        activeGeneralConversationId: 'general',
        activeRecipeConversationIds: {
          'recipe-1': 'recipe-current',
        },
        messagesByConversationId: {
          'recipe-current': [],
          'recipe-older': [],
        },
      });
    });
    mocks.deleteConversation.mockResolvedValue(undefined);
    mocks.fetchConversations.mockResolvedValue({
      conversations: [
        {
          id: 'recipe-older',
          title: 'Older',
          created_at: '2026-09-28T10:00:00Z',
          last_activity_at: '2026-09-28T10:00:00Z',
          recipe_context: {
            recipe_id: 'recipe-1',
            recipe_title: 'Pasta',
            is_current: true,
          },
        },
        {
          id: 'general',
          title: 'General',
          created_at: '2026-09-27T10:00:00Z',
          last_activity_at: '2026-09-27T10:00:00Z',
          recipe_context: null,
        },
      ],
      total: 2,
      has_more: false,
    });
    mocks.fetchMessages.mockResolvedValue({ messages: [], has_more: false });

    await act(async () => {
      await result.current.deleteConversation('recipe-current');
    });

    expect(result.current.activeConversationId).toBe('recipe-older');
    expect(result.current.activeRecipeConversationIds).toEqual({
      'recipe-1': 'recipe-older',
    });
    expect(result.current.activeGeneralConversationId).toBe('general');
    expect(
      result.current.messagesByConversationId['recipe-current']
    ).toBeUndefined();
    expect(mocks.fetchMessages).toHaveBeenCalledWith('recipe-older', 200);
  });

  test('deleteConversation preserves the active recipe when deleting its history', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'recipe-current',
            title: 'Current',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
          {
            id: 'recipe-history',
            title: 'History',
            createdAt: '2026-09-28T10:00:00Z',
            lastMessageAt: '2026-09-28T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: false,
            },
          },
        ],
        activeConversationId: 'recipe-current',
        activeRecipeConversationIds: {
          'recipe-1': 'recipe-current',
        },
      });
    });
    mocks.deleteConversation.mockResolvedValue(undefined);
    mocks.fetchConversations.mockResolvedValue({
      conversations: [
        {
          id: 'recipe-current',
          title: 'Current',
          created_at: '2026-09-29T10:00:00Z',
          last_activity_at: '2026-09-29T10:00:00Z',
          recipe_context: {
            recipe_id: 'recipe-1',
            recipe_title: 'Pasta',
            is_current: true,
          },
        },
      ],
      total: 1,
      has_more: false,
    });

    await act(async () => {
      await result.current.deleteConversation('recipe-history');
    });

    expect(result.current.activeConversationId).toBe('recipe-current');
    expect(result.current.activeRecipeConversationIds).toEqual({
      'recipe-1': 'recipe-current',
    });
    expect(mocks.fetchMessages).not.toHaveBeenCalled();
  });

  test('deleteConversation creates a contextual replacement for the last recipe thread', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'recipe-current',
            title: 'Current',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
        ],
        activeConversationId: 'recipe-current',
        activeRecipeConversationIds: {
          'recipe-1': 'recipe-current',
        },
      });
    });
    mocks.deleteConversation.mockResolvedValue(undefined);
    mocks.fetchConversations.mockResolvedValue({
      conversations: [],
      total: 0,
      has_more: false,
    });
    mocks.createRecipeConversation.mockResolvedValue({
      id: 'recipe-replacement',
      title: null,
      created_at: '2026-09-29T11:00:00Z',
      last_activity_at: '2026-09-29T11:00:00Z',
      recipe_context: {
        recipe_id: 'recipe-1',
        recipe_title: 'Pasta',
        is_current: true,
      },
    });

    await act(async () => {
      await result.current.deleteConversation('recipe-current');
    });

    expect(mocks.createRecipeConversation).toHaveBeenCalledWith('recipe-1');
    expect(result.current.activeConversationId).toBe('recipe-replacement');
    expect(result.current.activeRecipeConversationIds).toEqual({
      'recipe-1': 'recipe-replacement',
    });
    expect(result.current.conversations[0]?.recipeContext?.recipeId).toBe(
      'recipe-1'
    );
  });

  test('deleteConversation fails closed when contextual reconciliation cannot reload', async () => {
    const { result } = renderHook(() => useChatStore());
    const mocks = await getMocks();

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'recipe-current',
            title: 'Current',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Pasta',
              isCurrent: true,
            },
          },
        ],
        activeConversationId: 'recipe-current',
        activeRecipeConversationIds: {
          'recipe-1': 'recipe-current',
        },
        messagesByConversationId: {
          'recipe-current': [],
        },
      });
    });
    mocks.deleteConversation.mockResolvedValue(undefined);
    mocks.fetchConversations.mockRejectedValue(new Error('reload failed'));

    await act(async () => {
      await result.current.deleteConversation('recipe-current');
    });

    expect(result.current.activeConversationId).toBeNull();
    expect(result.current.activeRecipeConversationIds).toEqual({});
    expect(result.current.conversations).toEqual([]);
    expect(result.current.error).toBe(
      'The conversation was deleted, but recipe conversations could not be refreshed. Return to the recipe and try again.'
    );
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

describe('formatToolName', () => {
  test('returns friendly name for known tool', async () => {
    const { formatToolName } = await import('../useChatStore');

    expect(formatToolName('search_recipes')).toBe('Searching recipes...');
    expect(formatToolName('get_meal_plan_history')).toBe(
      'Analyzing meal history...'
    );
    expect(formatToolName('get_daily_weather')).toBe('Checking forecast...');
    expect(formatToolName('web_search')).toBe('Searching the web...');
    expect(formatToolName('fetch_url_as_markdown')).toBe('Reading web page...');
    expect(formatToolName('suggest_recipe')).toBe('Creating recipe draft...');
    expect(formatToolName('propose_meal_for_day')).toBe('Proposing meal...');
    expect(formatToolName('update_user_memory')).toBe('Updating memory...');
    expect(formatToolName('final_result')).toBe('Finalizing response...');
  });

  test('returns fallback for unknown tool', async () => {
    const { formatToolName } = await import('../useChatStore');

    expect(formatToolName('unknown_tool')).toBe('Using unknown_tool...');
    expect(formatToolName('custom_action')).toBe('Using custom_action...');
  });
});
