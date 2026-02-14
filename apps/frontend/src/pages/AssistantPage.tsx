import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { ChatInput } from '../components/chat/ChatInput';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ConversationList } from '../components/chat/ConversationList';
import { Container } from '../components/ui/Container';
import { useChatStore } from '../stores/useChatStore';

export default function AssistantPage() {
  const [searchParams] = useSearchParams();
  const hasHydrated = useChatStore((s) => s.hasHydrated);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const conversations = useChatStore((s) => s.conversations);
  const isLoading = useChatStore((s) => s.isLoading);
  const loadConversations = useChatStore((s) => s.loadConversations);
  const createConversation = useChatStore((s) => s.createConversation);
  const switchConversation = useChatStore((s) => s.switchConversation);
  const cancelPendingAssistantReply = useChatStore(
    (s) => s.cancelPendingAssistantReply
  );
  const messagesByConversationId = useChatStore(
    (s) => s.messagesByConversationId
  );

  const [announcement, setAnnouncement] = useState('');
  const lastAnnouncedMessageId = useRef<string | null>(null);
  const scrollContainerRef = useRef<HTMLElement | null>(null);
  const bottomAnchorRef = useRef<HTMLDivElement | null>(null);

  const messages = useMemo(() => {
    if (!activeConversationId) return [];
    return messagesByConversationId[activeConversationId] ?? [];
  }, [activeConversationId, messagesByConversationId]);

  const lastMessage = useMemo(() => {
    return messages.length > 0 ? messages[messages.length - 1] : null;
  }, [messages]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  // Poll conversations to pick up title updates
  // Use 30s in development, 60s in production to reduce API calls
  useEffect(() => {
    if (!hasHydrated) return;

    const pollInterval = import.meta.env.MODE === 'development' ? 30000 : 60000; // 30s dev, 60s prod

    const intervalId = setInterval(() => {
      void loadConversations();
    }, pollInterval);

    return () => clearInterval(intervalId);
  }, [hasHydrated, loadConversations]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!hasHydrated) return;

      const key = e.key.toLowerCase();
      const isModifierPressed = e.metaKey || e.ctrlKey;

      if (!isModifierPressed) return;

      if (key === 'k') {
        e.preventDefault();
        document
          .querySelector<
            HTMLInputElement | HTMLTextAreaElement
          >('#assistant-message')
          ?.focus();
        return;
      }

      if (key === 'n') {
        e.preventDefault();
        void createConversation();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [createConversation, hasHydrated]);

  useEffect(() => {
    return () => {
      cancelPendingAssistantReply();
    };
  }, [cancelPendingAssistantReply]);

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

  useEffect(() => {
    if (!hasHydrated) return;

    const requestedConversationId = searchParams.get('conversationId');
    if (!requestedConversationId) return;
    if (requestedConversationId === activeConversationId) return;

    const exists = conversations.some((c) => c.id === requestedConversationId);
    if (!exists) return;

    void switchConversation(requestedConversationId);
  }, [
    activeConversationId,
    conversations,
    hasHydrated,
    searchParams,
    switchConversation,
  ]);

  useEffect(() => {
    if (!hasHydrated) return;
    if (!lastMessage) return;

    if (lastMessage.id === lastAnnouncedMessageId.current) return;
    lastAnnouncedMessageId.current = lastMessage.id;

    if (lastMessage.role === 'assistant') {
      setAnnouncement(`Nibble: ${lastMessage.content}`);
    }
  }, [hasHydrated, lastMessage]);

  useEffect(() => {
    if (!hasHydrated) return;
    if (!lastMessage) return;

    const container = scrollContainerRef.current;
    const anchor = bottomAnchorRef.current;
    if (!container || !anchor) return;

    const isNearBottom =
      container.scrollTop + container.clientHeight >=
      container.scrollHeight - 40;

    if (isNearBottom || lastMessage.role === 'assistant') {
      if (typeof anchor.scrollIntoView === 'function') {
        anchor.scrollIntoView({ block: 'end' });
      } else {
        // jsdom doesn't implement scrollIntoView; fall back to manual scroll.
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [hasHydrated, lastMessage]);

  return (
    <Container as="main" size="xl" className="py-4 md:py-6">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {announcement}
      </div>
      <div className="flex h-[calc(100dvh-8rem)] flex-col md:flex-row">
        <aside
          aria-label="Conversation list"
          className="hidden w-80 shrink-0 border-r border-gray-200 md:block md:overflow-y-auto"
        >
          <ConversationList />
        </aside>

        <section
          aria-label="Chat conversation"
          className="flex min-h-0 min-w-0 flex-1 flex-col md:pl-6"
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

          <section
            aria-label="Conversation"
            className="min-h-0 flex-1 overflow-y-auto rounded-md border border-gray-200 bg-white p-4"
            ref={(el) => {
              scrollContainerRef.current = el;
            }}
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
              <ol role="list" className="space-y-4">
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
              </ol>
            )}

            {isLoading ? (
              <p className="text-sm text-gray-500" aria-live="polite">
                Nibble is typing…
              </p>
            ) : null}

            <div ref={bottomAnchorRef} />
          </section>

          <div className="shrink-0 border-t border-gray-200 pt-4">
            <ChatInput />
          </div>
        </section>
      </div>
    </Container>
  );
}
