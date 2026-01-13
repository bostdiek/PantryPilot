import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { act } from 'react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { useChatStore } from '../../../stores/useChatStore';
import { ConversationList } from '../ConversationList';

describe('ConversationList', () => {
  beforeEach(() => {
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

  test('compact mode shows empty state and disables selector when no chats', () => {
    render(<ConversationList compact />);

    const selector = screen.getByLabelText('Select a conversation');
    expect(selector).toBeDisabled();
    expect(screen.getByText('No chats yet')).toBeInTheDocument();
  });

  test('compact mode allows switching conversations and creating a new chat', async () => {
    const createSpy = vi.spyOn(useChatStore.getState(), 'createConversation');
    const switchSpy = vi.spyOn(useChatStore.getState(), 'switchConversation');

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat 1',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-02T00:00:00.000Z').toISOString(),
          },
          {
            id: 'c2',
            title: 'Chat 2',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-03T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
      });
    });

    render(<ConversationList compact />);

    fireEvent.change(screen.getByLabelText('Select a conversation'), {
      target: { value: 'c2' },
    });

    expect(switchSpy).toHaveBeenCalledWith('c2');

    fireEvent.click(screen.getByRole('button', { name: 'New Chat' }));
    expect(createSpy).toHaveBeenCalled();
  });

  test('desktop list shows empty state when no chats', () => {
    render(<ConversationList />);

    expect(screen.getByText('No chats yet.')).toBeInTheDocument();
  });

  test('desktop list renders conversations and highlights the active one', () => {
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat 1',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-02T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
      });
    });

    render(<ConversationList />);

    const item = screen.getByRole('button', { name: /Chat 1/i });
    expect(item).toHaveAttribute('aria-current', 'page');
  });

  test('desktop list switches conversations when clicking an inactive item', () => {
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat 1',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-02T00:00:00.000Z').toISOString(),
          },
          {
            id: 'c2',
            title: 'Chat 2',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-03T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
      });
    });

    render(<ConversationList />);

    expect(screen.getByRole('button', { name: /Chat 1/i })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByRole('button', { name: /Chat 2/i })).not.toHaveAttribute(
      'aria-current'
    );

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Chat 2/i }));
    });

    expect(useChatStore.getState().activeConversationId).toBe('c2');
    expect(screen.getByRole('button', { name: /Chat 2/i })).toHaveAttribute(
      'aria-current',
      'page'
    );
  });
});
