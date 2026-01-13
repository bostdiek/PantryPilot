import { Send } from 'lucide-react';
import {
  useCallback,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from 'react';

import { useChatStore } from '../../stores/useChatStore';
import { Button } from '../ui/Button';
import { Textarea } from '../ui/Textarea';

export function ChatInput() {
  const [message, setMessage] = useState('');
  const isLoading = useChatStore((s) => s.isLoading);
  const sendMessage = useChatStore((s) => s.sendMessage);

  const sendCurrentMessage = useCallback(async () => {
    const trimmed = message.trim();
    if (!trimmed || isLoading) return;

    await sendMessage(trimmed);
    setMessage('');
  }, [isLoading, message, sendMessage]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await sendCurrentMessage();
  };

  const handleKeyDown = async (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      await sendCurrentMessage();
      return;
    }

    if (e.key === 'Escape') {
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <label className="sr-only" htmlFor="assistant-message">
        Message Nibble
      </label>
      <p id="assistant-message-help" className="sr-only">
        Press Enter to send. Press Shift plus Enter for a new line.
      </p>

      <Textarea
        id="assistant-message"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={2}
        disabled={isLoading}
        placeholder="Ask Nibble about a recipe, ingredient, or meal idea…"
        aria-label="Message Nibble"
        aria-describedby="assistant-message-help"
        className="min-h-12 flex-1 border-gray-500 bg-white shadow-sm placeholder:text-gray-500 disabled:bg-gray-100"
      />

      <Button
        type="submit"
        variant="primary"
        disabled={!message.trim() || isLoading}
        className="h-12 w-12 shrink-0 p-0"
        aria-label="Send message"
      >
        <Send className="h-5 w-5" aria-hidden="true" />
      </Button>
    </form>
  );
}
