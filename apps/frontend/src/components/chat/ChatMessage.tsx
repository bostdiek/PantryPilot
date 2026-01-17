import { useMemo } from 'react';

import type { ChatContentBlock } from '../../types/Chat';

import {
  ActionBlock,
  LinkBlock,
  RecipeCardBlock,
  TextBlock,
  UnknownBlock,
} from './blocks';

/** Message type that supports both legacy content and new blocks format */
export interface ChatMessageData {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant';
  /** Plain text content (user messages, or legacy assistant messages) */
  content?: string;
  /** Structured content blocks (assistant messages) */
  blocks?: ChatContentBlock[];
  createdAt: string;
  /** Whether the message is still being streamed */
  isStreaming?: boolean;
}

interface ChatMessageProps {
  message: ChatMessageData;
  /** Callback when an action is accepted */
  onAcceptAction?: (actionId: string) => Promise<void>;
  /** Callback when an action is canceled */
  onCancelAction?: (actionId: string) => Promise<void>;
}

/**
 * Renders a single block based on its type.
 */
function renderBlock(
  block: ChatContentBlock,
  index: number,
  onAcceptAction?: (actionId: string) => Promise<void>,
  onCancelAction?: (actionId: string) => Promise<void>
) {
  const key = `block-${index}`;

  switch (block.type) {
    case 'text':
      return <TextBlock key={key} block={block} />;
    case 'link':
      return <LinkBlock key={key} block={block} />;
    case 'recipe_card':
      return <RecipeCardBlock key={key} block={block} />;
    case 'action':
      return (
        <ActionBlock
          key={key}
          block={block}
          onAccept={onAcceptAction}
          onCancel={onCancelAction}
        />
      );
    default:
      return <UnknownBlock key={key} block={block} />;
  }
}

export function ChatMessage({
  message,
  onAcceptAction,
  onCancelAction,
}: ChatMessageProps) {
  const isUser = message.role === 'user';

  const formattedTime = useMemo(() => {
    return new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(message.createdAt));
  }, [message.createdAt]);

  const speaker = isUser ? 'You' : 'Nibble';

  // Determine content to render
  const renderContent = () => {
    // User messages always render as plain text
    if (isUser) {
      return (
        <div className="text-base leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      );
    }

    // Assistant messages: prefer blocks, fall back to content
    if (message.blocks && message.blocks.length > 0) {
      return (
        <div className="space-y-1">
          {message.blocks.map((block, index) =>
            renderBlock(block, index, onAcceptAction, onCancelAction)
          )}
          {message.isStreaming && (
            <div className="flex items-center gap-1 text-gray-500">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-gray-400" />
              <span className="text-xs">Typing...</span>
            </div>
          )}
        </div>
      );
    }

    // Legacy assistant message with plain content
    if (message.content) {
      return (
        <div className="text-base leading-relaxed whitespace-pre-wrap">
          {message.content}
          {message.isStreaming && (
            <span className="ml-1 inline-block h-2 w-2 animate-pulse rounded-full bg-gray-400" />
          )}
        </div>
      );
    }

    // Streaming message with no content yet
    if (message.isStreaming) {
      return (
        <div className="flex items-center gap-1 text-gray-500">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-gray-400" />
          <span className="text-xs">Typing...</span>
        </div>
      );
    }

    return null;
  };

  return (
    <li className={isUser ? 'flex justify-end' : 'flex justify-start'}>
      <article role="article" aria-label={`${speaker} message`}>
        <div
          className={
            isUser
              ? 'bg-primary-600 max-w-[80%] rounded-lg p-3 text-white'
              : 'max-w-[80%] rounded-lg bg-gray-100 p-3 text-gray-900'
          }
        >
          {renderContent()}
          <div
            className={
              isUser
                ? 'text-primary-100 mt-1 text-xs'
                : 'mt-1 text-xs text-gray-500'
            }
          >
            <span className="sr-only">{speaker} at </span>
            {formattedTime}
          </div>
        </div>
      </article>
    </li>
  );
}
