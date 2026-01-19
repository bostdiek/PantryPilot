import clsx from 'clsx';
import { Plus, Trash2 } from 'lucide-react';
import type React from 'react';

import { useChatStore, type Conversation } from '../../stores/useChatStore';
import { Button } from '../ui/Button';

interface ConversationListProps {
  compact?: boolean;
}

function formatLastMessageAt(conversation: Conversation): string {
  const date = new Date(conversation.lastMessageAt);

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
  }).format(date);
}

export function ConversationList({ compact = false }: ConversationListProps) {
  const conversations = useChatStore((s) => s.conversations);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const createConversation = useChatStore((s) => s.createConversation);
  const switchConversation = useChatStore((s) => s.switchConversation);
  const deleteConversation = useChatStore((s) => s.deleteConversation);

  const handleDeleteConversation = (
    e: React.MouseEvent,
    conversationId: string,
    conversationTitle: string | null
  ) => {
    e.stopPropagation(); // Prevent switching to the conversation

    const confirmed = window.confirm(
      `Are you sure you want to delete "${conversationTitle || 'this conversation'}"? This action cannot be undone.`
    );

    if (confirmed) {
      void deleteConversation(conversationId);
    }
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <label className="sr-only" htmlFor="assistant-conversation">
          Conversation
        </label>
        <select
          id="assistant-conversation"
          value={activeConversationId ?? ''}
          onChange={(e) => void switchConversation(e.target.value)}
          className="h-12 min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 text-base focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
          disabled={conversations.length === 0}
          aria-label="Select a conversation"
        >
          {conversations.length === 0 ? (
            <option value="">No chats yet</option>
          ) : null}
          {conversations.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}
            </option>
          ))}
        </select>

        <Button
          type="button"
          variant="primary"
          className="h-12 w-12 shrink-0 p-0"
          onClick={() => void createConversation()}
          aria-label="New Chat"
          title="New Chat"
        >
          <Plus className="h-6 w-6" aria-hidden="true" />
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-gray-200 p-4">
        <Button
          type="button"
          variant="primary"
          fullWidth
          className="h-12"
          onClick={() => void createConversation()}
        >
          <span className="inline-flex items-center gap-2">
            <Plus className="h-5 w-5" aria-hidden="true" />
            <span>New Chat</span>
          </span>
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {conversations.map((c) => (
          <div
            key={c.id}
            className={clsx(
              'group relative min-h-[60px] border-b border-gray-100',
              activeConversationId === c.id ? 'bg-primary-50' : 'hover:bg-gray-50'
            )}
          >
            <button
              type="button"
              onClick={() => void switchConversation(c.id)}
              aria-current={activeConversationId === c.id ? 'page' : undefined}
              className="w-full p-4 pr-12 text-left focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 focus:outline-none"
            >
              <div className="truncate font-medium text-gray-900">
                {c.title}
              </div>
              <div className="mt-1 text-sm text-gray-500">
                {formatLastMessageAt(c)}
              </div>
            </button>
            <button
              type="button"
              onClick={(e) => handleDeleteConversation(e, c.id, c.title)}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-2 text-gray-400 opacity-0 transition-opacity hover:bg-gray-100 hover:text-red-600 focus:opacity-100 focus:ring-2 focus:ring-blue-500 focus:outline-none group-hover:opacity-100"
              aria-label={`Delete conversation "${c.title}"`}
              title="Delete conversation"
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ))}

        {conversations.length === 0 ? (
          <div className="p-4 text-sm text-gray-600">No chats yet.</div>
        ) : null}
      </div>
    </div>
  );
}
