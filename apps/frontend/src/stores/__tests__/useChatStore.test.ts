import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { useChatStore } from '../useChatStore';

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
      });
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
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

    await act(async () => {
      await result.current.createConversation('Chat 1');
    });

    const convoId = result.current.conversations[0]!.id;

    await act(async () => {
      await result.current.switchConversation(convoId);
    });

    expect(result.current.activeConversationId).toBe(convoId);
  });

  test('loadConversations toggles loading state', async () => {
    const { result } = renderHook(() => useChatStore());

    const transitions: boolean[] = [];
    const unsubscribe = useChatStore.subscribe((state) => {
      transitions.push(state.isLoading);
    });

    let promise: Promise<void> | undefined;
    act(() => {
      promise = result.current.loadConversations();
    });

    await act(async () => {
      await promise;
    });

    unsubscribe();

    expect(transitions).toContain(true);
    expect(useChatStore.getState().isLoading).toBe(false);

    expect(useChatStore.getState().isLoading).toBe(false);
  });

  test('sendMessage creates a conversation if none exists and appends a user + assistant message', async () => {
    const { result } = renderHook(() => useChatStore());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    const conversationId = useChatStore.getState().activeConversationId;
    expect(conversationId).not.toBeNull();

    const afterUser =
      useChatStore.getState().messagesByConversationId[conversationId!];
    expect(afterUser).toHaveLength(1);
    expect(afterUser?.[0]?.role).toBe('user');

    act(() => {
      vi.advanceTimersByTime(700);
    });

    const afterAssistant =
      useChatStore.getState().messagesByConversationId[conversationId!];
    expect(afterAssistant).toHaveLength(2);
    expect(afterAssistant?.[1]?.role).toBe('assistant');
    expect(useChatStore.getState().isLoading).toBe(false);
  });

  test('sendMessage ignores empty/whitespace input', async () => {
    const { result } = renderHook(() => useChatStore());

    await act(async () => {
      await result.current.sendMessage('   ');
    });

    expect(useChatStore.getState().conversations).toHaveLength(0);
  });

  test('cancelPendingAssistantReply cancels the scheduled assistant message', async () => {
    const { result } = renderHook(() => useChatStore());

    await act(async () => {
      await result.current.createConversation('Chat');
      await result.current.sendMessage('Hello');
    });

    const conversationId = useChatStore.getState().activeConversationId!;
    expect(useChatStore.getState().isLoading).toBe(true);
    expect(
      useChatStore.getState().messagesByConversationId[conversationId]
    ).toHaveLength(1);

    act(() => {
      result.current.cancelPendingAssistantReply();
    });

    expect(useChatStore.getState().isLoading).toBe(false);

    act(() => {
      vi.advanceTimersByTime(700);
    });

    expect(
      useChatStore.getState().messagesByConversationId[conversationId]
    ).toHaveLength(1);
  });

  test('clearConversation clears messages for the given conversation', async () => {
    const { result } = renderHook(() => useChatStore());

    await act(async () => {
      await result.current.createConversation('Chat');
      await result.current.sendMessage('Hello');
    });

    const conversationId = useChatStore.getState().activeConversationId!;

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

  test('caps messages at 50 per conversation', async () => {
    const { result } = renderHook(() => useChatStore());

    await act(async () => {
      await result.current.createConversation('Chat');
    });

    const conversationId = useChatStore.getState().activeConversationId!;

    act(() => {
      useChatStore.setState({
        messagesByConversationId: {
          [conversationId]: Array.from({ length: 50 }, (_, i) => ({
            id: `m${i}`,
            conversationId,
            role: 'user',
            content: `msg ${i}`,
            createdAt: new Date(2026, 0, 1, 0, 0, i).toISOString(),
          })),
        },
      });
    });

    await act(async () => {
      await result.current.sendMessage('overflow');
    });

    const afterUser =
      useChatStore.getState().messagesByConversationId[conversationId];
    expect(afterUser).toHaveLength(50);
    expect(afterUser[49]?.content).toBe('overflow');

    act(() => {
      vi.advanceTimersByTime(700);
    });

    const afterAssistant =
      useChatStore.getState().messagesByConversationId[conversationId];
    expect(afterAssistant).toHaveLength(50);
    expect(afterAssistant[49]?.role).toBe('assistant');
  });
});
