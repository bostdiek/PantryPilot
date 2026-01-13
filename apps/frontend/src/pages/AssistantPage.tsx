import { useEffect, useMemo } from 'react';

import { ChatInput } from '../components/chat/ChatInput';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ConversationList } from '../components/chat/ConversationList';
import { Container } from '../components/ui/Container';
import { useChatStore } from '../stores/useChatStore';

export default function AssistantPage() {
  const hasHydrated = useChatStore((s) => s.hasHydrated);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const conversations = useChatStore((s) => s.conversations);
  const isLoading = useChatStore((s) => s.isLoading);
  const loadConversations = useChatStore((s) => s.loadConversations);
  const createConversation = useChatStore((s) => s.createConversation);
  const switchConversation = useChatStore((s) => s.switchConversation);
  const messagesByConversationId = useChatStore(
    (s) => s.messagesByConversationId
  );

  const messages = useMemo(() => {
    if (!activeConversationId) return [];
    return messagesByConversationId[activeConversationId] ?? [];
  }, [activeConversationId, messagesByConversationId]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (!hasHydrated) return;

    if (conversations.length === 0) {
      void createConversation();
      return;
    }

    if (!activeConversationId) {
      void switchConversation(conversations[0].id);
    }
  }, [
    activeConversationId,
    conversations,
    createConversation,
    hasHydrated,
    switchConversation,
  ]);

  return (
    <Container as="main" size="xl" className="py-4 md:py-6">
      <div className="flex min-h-[calc(100dvh-5rem)] flex-col md:flex-row">
        <aside
          aria-label="Conversation list"
          className="hidden w-[300px] shrink-0 border-r border-gray-200 md:block"
        >
          <ConversationList />
        </aside>

        <section
          aria-label="Chat conversation"
          className="flex min-w-0 flex-1 flex-col md:pl-6"
        >
          <header className="pb-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold">SmartMeal Assistant</h1>
                <p className="mt-1 text-sm text-gray-600">
                  Nibble is here to help you plan meals and groceries.
                </p>
              </div>

              <button
                type="button"
                onClick={() => void createConversation()}
                className="hidden h-12 rounded-lg border border-gray-300 px-4 text-base font-medium hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 focus:outline-none md:inline-flex"
              >
                New Chat
              </button>
            </div>

            <div className="mt-3 md:hidden" aria-label="Conversation selector">
              <ConversationList compact />
            </div>
          </header>

          <article
            aria-label="Conversation"
            className="min-h-0 flex-1 space-y-4 overflow-y-auto rounded-md border border-gray-200 bg-white p-4"
          >
            {!hasHydrated ? (
              <p className="text-sm text-gray-600">Loading…</p>
            ) : messages.length === 0 ? (
              <div className="text-center text-gray-600">
                <p className="text-base">
                  Start a conversation with Nibble to get cooking guidance.
                </p>
              </div>
            ) : (
              messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
            )}

            {isLoading ? (
              <p className="text-sm text-gray-500" aria-live="polite">
                Nibble is typing…
              </p>
            ) : null}
          </article>

          <div className="border-t border-gray-200 pt-4">
            <ChatInput />
          </div>
        </section>
      </div>
    </Container>
  );
}
