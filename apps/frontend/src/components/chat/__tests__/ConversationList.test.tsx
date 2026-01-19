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

    // Get all buttons with "Chat 1" in the name (conversation button + delete button)
    // The conversation button is the one with aria-current
    const chat1Buttons = screen.getAllByRole('button', { name: /Chat 1/i });
    const chat1ConversationButton = chat1Buttons.find(
      (btn) => btn.getAttribute('aria-current') === 'page'
    );
    expect(chat1ConversationButton).toHaveAttribute('aria-current', 'page');
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

    // Get conversation buttons (not delete buttons)
    const chat1Buttons = screen.getAllByRole('button', { name: /Chat 1/i });
    const chat1ConversationButton = chat1Buttons.find(
      (btn) => btn.getAttribute('aria-current') === 'page'
    );
    expect(chat1ConversationButton).toHaveAttribute('aria-current', 'page');

    const chat2Buttons = screen.getAllByRole('button', { name: /Chat 2/i });
    const chat2ConversationButton = chat2Buttons.find(
      (btn) => !btn.getAttribute('aria-label')?.startsWith('Delete')
    );
    expect(chat2ConversationButton).not.toHaveAttribute('aria-current');

    // Click on Chat 2 conversation button (not the delete button)
    act(() => {
      fireEvent.click(chat2ConversationButton!);
    });

    expect(useChatStore.getState().activeConversationId).toBe('c2');

    // After clicking, Chat 2 should now be active
    const chat2ButtonsAfterClick = screen.getAllByRole('button', {
      name: /Chat 2/i,
    });
    const chat2ActiveButton = chat2ButtonsAfterClick.find(
      (btn) => btn.getAttribute('aria-current') === 'page'
    );
    expect(chat2ActiveButton).toHaveAttribute('aria-current', 'page');
  });
});
