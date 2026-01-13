import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { ChatMessage } from '../ChatMessage';

describe('ChatMessage', () => {
  test('renders a user message with accessible label', () => {
    render(
      <ol>
        <ChatMessage
          message={{
            id: 'm1',
            conversationId: 'c1',
            role: 'user',
            content: 'Hello',
            createdAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
          }}
        />
      </ol>
    );

    expect(screen.getByLabelText('You message')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('You at')).toBeInTheDocument();
  });

  test('renders an assistant message with accessible label', () => {
    render(
      <ol>
        <ChatMessage
          message={{
            id: 'm2',
            conversationId: 'c1',
            role: 'assistant',
            content: 'Hi there!',
            createdAt: new Date('2026-01-01T01:00:10.000Z').toISOString(),
          }}
        />
      </ol>
    );

    expect(screen.getByLabelText('Nibble message')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
    expect(screen.getByText('Nibble at')).toBeInTheDocument();
  });
});
