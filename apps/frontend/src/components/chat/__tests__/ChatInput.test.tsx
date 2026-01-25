import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { act } from 'react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { useChatStore } from '../../../stores/useChatStore';
import { ChatInput } from '../ChatInput';

describe('ChatInput', () => {
  beforeEach(() => {
    vi.useRealTimers();
    localStorage.clear();

    act(() => {
      useChatStore.setState({
        hasHydrated: true,
        isLoading: false,
        activeConversationId: 'c1',
        conversations: [
          {
            id: 'c1',
            title: 'Chat with Nibble',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
          },
        ],
        messagesByConversationId: { c1: [] },
      });

      // Override sendMessage so these tests focus on input behavior.
      useChatStore.setState({
        sendMessage: vi.fn().mockResolvedValue(undefined),
      } as any);
    });
  });

  test('uses a single-line input on mobile (voice-typing friendly)', () => {
    const originalMatchMedia = window.matchMedia;

    window.matchMedia = ((query: string) =>
      ({
        matches: true,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }) as any) as any;

    try {
      render(<ChatInput />);
      const composer = screen.getByLabelText('Message Nibble');
      expect((composer as HTMLElement).tagName).toBe('INPUT');
    } finally {
      window.matchMedia = originalMatchMedia;
    }
  });

  test('disables send when empty and enables when there is input', async () => {
    const user = userEvent.setup();

    render(<ChatInput />);

    const sendButton = screen.getByRole('button', { name: 'Send message' });
    expect(sendButton).toBeDisabled();

    await user.type(screen.getByLabelText('Message Nibble'), 'Hi');
    expect(sendButton).toBeEnabled();
  });

  test('Enter sends trimmed message and clears the input', async () => {
    const user = userEvent.setup();
    const sendMessage = useChatStore.getState()
      .sendMessage as unknown as ReturnType<typeof vi.fn>;

    render(<ChatInput />);

    const composer = screen.getByLabelText('Message Nibble');
    await user.type(composer, '  hello  ');
    await user.keyboard('{Enter}');

    expect(sendMessage).toHaveBeenCalledWith('hello');
    expect(composer).toHaveValue('');
  });

  test('Shift+Enter does not send', async () => {
    const user = userEvent.setup();
    const sendMessage = useChatStore.getState()
      .sendMessage as unknown as ReturnType<typeof vi.fn>;

    render(<ChatInput />);

    const composer = screen.getByLabelText('Message Nibble');
    await user.type(composer, 'hello');
    await user.keyboard('{Shift>}{Enter}{/Shift}');

    expect(sendMessage).not.toHaveBeenCalled();
    const value = (composer as HTMLTextAreaElement).value;
    expect(value).toMatch(/^hello\s*\n/);
  });

  test('Escape clears the input', async () => {
    const user = userEvent.setup();

    render(<ChatInput />);

    const composer = screen.getByLabelText('Message Nibble');
    await user.type(composer, 'hello');
    await user.keyboard('{Escape}');

    expect(composer).toHaveValue('');
  });

  test('keeps composer enabled when loading (dictation-friendly), but disables send', () => {
    act(() => {
      useChatStore.setState({ isLoading: true });
    });

    render(<ChatInput />);

    expect(screen.getByLabelText('Message Nibble')).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled();
  });

  test('does not send when loading (defensive guard)', async () => {
    const user = userEvent.setup();
    const sendMessage = useChatStore.getState()
      .sendMessage as unknown as ReturnType<typeof vi.fn>;

    render(<ChatInput />);

    const composer = screen.getByLabelText('Message Nibble');
    await user.type(composer, 'hello');

    act(() => {
      useChatStore.setState({ isLoading: true });
    });

    const form = composer.closest('form');
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    expect(sendMessage).not.toHaveBeenCalled();
    expect(composer).toHaveValue('hello');
  });
});
