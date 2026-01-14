import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { act } from 'react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { useChatStore } from '../../stores/useChatStore';
import AssistantPage from '../AssistantPage';

describe('AssistantPage', () => {
  beforeEach(() => {
    vi.useRealTimers();
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

  test('renders the heading and help text', async () => {
    const loadSpy = vi.spyOn(useChatStore.getState(), 'loadConversations');

    render(<AssistantPage />);

    expect(
      screen.getByRole('heading', { name: 'SmartMeal Assistant' })
    ).toBeInTheDocument();
    expect(
      screen.getByText('Nibble is here to help you plan meals and groceries.')
    ).toBeInTheDocument();

    await waitFor(() => expect(loadSpy).toHaveBeenCalled());
  });

  test('shows a loading state when not hydrated', () => {
    act(() => {
      useChatStore.setState({ hasHydrated: false });
    });

    render(<AssistantPage />);

    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  test('creates a conversation on first hydrate when empty', async () => {
    const createSpy = vi.spyOn(useChatStore.getState(), 'createConversation');

    render(<AssistantPage />);

    await waitFor(() => expect(createSpy).toHaveBeenCalled());
  });

  test('switches to the first conversation when conversations exist but none selected', async () => {
    const switchSpy = vi.spyOn(useChatStore.getState(), 'switchConversation');

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat with Nibble',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: null,
        messagesByConversationId: { c1: [] },
      });
    });

    render(<AssistantPage />);

    await waitFor(() => expect(switchSpy).toHaveBeenCalledWith('c1'));
  });

  test('renders messages as a semantic list', () => {
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat with Nibble',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
        messagesByConversationId: {
          c1: [
            {
              id: 'm1',
              conversationId: 'c1',
              role: 'user',
              content: 'Hello',
              createdAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
            },
            {
              id: 'm2',
              conversationId: 'c1',
              role: 'assistant',
              content: 'Hi! I am Nibble.',
              createdAt: new Date('2026-01-01T01:00:10.000Z').toISOString(),
            },
          ],
        },
      });
    });

    render(<AssistantPage />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi! I am Nibble.')).toBeInTheDocument();
    expect(screen.getByLabelText('You message')).toBeInTheDocument();
    expect(screen.getByLabelText('Nibble message')).toBeInTheDocument();
  });

  test('Cmd/Ctrl+K focuses the composer and Cmd/Ctrl+N creates a new chat', async () => {
    const user = userEvent.setup();
    const createSpy = vi.spyOn(useChatStore.getState(), 'createConversation');

    render(<AssistantPage />);

    const composer = screen.getByLabelText('Message Nibble');
    expect(composer).not.toHaveFocus();

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'k', metaKey: true })
    );
    await waitFor(() => expect(composer).toHaveFocus());

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'n', ctrlKey: true })
    );
    await waitFor(() => expect(createSpy).toHaveBeenCalled());

    // sanity: keyboard handler does not block normal typing
    await user.type(composer, 'test');
    expect(screen.getByDisplayValue('test')).toBeInTheDocument();
  });

  test('announces new assistant messages via a polite live region', async () => {
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat with Nibble',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
        messagesByConversationId: {
          c1: [
            {
              id: 'm2',
              conversationId: 'c1',
              role: 'assistant',
              content: 'Welcome!',
              createdAt: new Date('2026-01-01T01:00:10.000Z').toISOString(),
            },
          ],
        },
      });
    });

    render(<AssistantPage />);

    const status = screen.getByRole('status');
    await waitFor(() => expect(status).toHaveTextContent('Nibble: Welcome!'));
  });
});
