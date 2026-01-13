import { useMemo } from 'react';

import type { Message } from '../../stores/useChatStore';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  const formattedTime = useMemo(() => {
    return new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(message.createdAt));
  }, [message.createdAt]);

  const speaker = isUser ? 'You' : 'Nibble';

  return (
    <article
      role="article"
      aria-label={`${speaker} message`}
      className={isUser ? 'flex justify-end' : 'flex justify-start'}
    >
      <div
        className={
          isUser
            ? 'bg-primary-600 max-w-[80%] rounded-lg p-3 text-white'
            : 'max-w-[80%] rounded-lg bg-gray-100 p-3 text-gray-900'
        }
      >
        <div className="text-base leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
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
  );
}
