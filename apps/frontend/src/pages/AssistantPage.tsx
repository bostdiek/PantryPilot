import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { ChatInput } from '../components/chat/ChatInput';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ConversationList } from '../components/chat/ConversationList';
import { Container } from '../components/ui/Container';
import { useChatStore } from '../stores/useChatStore';

interface AssistantLocationState {
  recipeContext?: {
    recipeId: string;
    recipeTitle: string;
  };
  recipeOrigin?: {
    pathname: string;
    scrollY: number;
    triggerId: string;
  };
}

export default function AssistantPage() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const locationState = location.state as AssistantLocationState | null;
  const requestedRecipeContext = locationState?.recipeContext;
  const requestedRecipeId = requestedRecipeContext?.recipeId;
  const lastRecipeResumeAttemptRef = useRef<string | null>(null);
  const generalCreationRequestedRef = useRef(false);
  const hasHydrated = useChatStore((s) => s.hasHydrated);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const conversations = useChatStore((s) => s.conversations);
  const confirmedRecipeConversationIds = useChatStore(
    (s) => s.confirmedRecipeConversationIds
  );
  const isLoading = useChatStore((s) => s.isLoading);
  const error = useChatStore((s) => s.error);
  const loadConversations = useChatStore((s) => s.loadConversations);
  const createConversation = useChatStore((s) => s.createConversation);
  const resumeRecipeConversation = useChatStore(
    (s) => s.resumeRecipeConversation
  );
  const createRecipeConversation = useChatStore(
    (s) => s.createRecipeConversation
  );
  const switchConversation = useChatStore((s) => s.switchConversation);
  const clearError = useChatStore((s) => s.clearError);
  const cancelPendingAssistantReply = useChatStore(
    (s) => s.cancelPendingAssistantReply
  );
  const messagesByConversationId = useChatStore(
    (s) => s.messagesByConversationId
  );
  const hasPreviousMessagesByConversationId = useChatStore(
    (s) => s.hasPreviousMessagesByConversationId
  );
  const loadMoreMessages = useChatStore((s) => s.loadMoreMessages);

  const [announcement, setAnnouncement] = useState('');
  const lastAnnouncedMessageId = useRef<string | null>(null);
  const scrollContainerRef = useRef<HTMLElement | null>(null);
  const bottomAnchorRef = useRef<HTMLDivElement | null>(null);

  const messages = useMemo(() => {
    if (!activeConversationId) return [];
    return messagesByConversationId[activeConversationId] ?? [];
  }, [activeConversationId, messagesByConversationId]);

  const activeConversation = useMemo(
    () =>
      conversations.find(
        (conversation) => conversation.id === activeConversationId
      ),
    [activeConversationId, conversations]
  );
  const activeRecipeContext =
    activeConversation?.recipeContext ??
    (activeConversationId ? undefined : requestedRecipeContext);
  const isRequestedRecipeConversationActive =
    !requestedRecipeId ||
    (activeConversation?.recipeContext?.recipeId === requestedRecipeId &&
      confirmedRecipeConversationIds[requestedRecipeId] ===
        activeConversation.id);

  const handleNewGeneralChat = useCallback(() => {
    clearError();
    generalCreationRequestedRef.current = true;
    if (requestedRecipeId) {
      navigate('/assistant', { replace: true, state: null });
    }
    void createConversation();
  }, [clearError, createConversation, navigate, requestedRecipeId]);

  const handleSelectConversation = useCallback(
    async (conversationId: string) => {
      await switchConversation(conversationId);
      const selectedConversation = useChatStore
        .getState()
        .conversations.find(
          (conversation) => conversation.id === conversationId
        );
      const selectedRecipeContext = selectedConversation?.recipeContext;

      if (!selectedRecipeContext) {
        if (requestedRecipeId) {
          navigate('/assistant', { replace: true, state: null });
        }
        return;
      }

      const selectedRecipePath = `/recipes/${selectedRecipeContext.recipeId}`;
      const recipeOrigin =
        locationState?.recipeOrigin?.pathname === selectedRecipePath
          ? locationState.recipeOrigin
          : undefined;
      navigate('/assistant', {
        replace: true,
        state: {
          recipeContext: {
            recipeId: selectedRecipeContext.recipeId,
            recipeTitle: selectedRecipeContext.recipeTitle,
          },
          ...(recipeOrigin ? { recipeOrigin } : {}),
        },
      });
    },
    [
      locationState?.recipeOrigin,
      navigate,
      requestedRecipeId,
      switchConversation,
    ]
  );

  const hasPreviousMessages = activeConversationId
    ? (hasPreviousMessagesByConversationId[activeConversationId] ?? false)
    : false;

  const lastMessage = useMemo(() => {
    return messages.length > 0 ? messages[messages.length - 1] : null;
  }, [messages]);

  useEffect(() => {
    let cancelled = false;

    const initializeConversations = async () => {
      await loadConversations();
      if (
        cancelled ||
        !requestedRecipeId ||
        lastRecipeResumeAttemptRef.current === requestedRecipeId
      ) {
        return;
      }

      lastRecipeResumeAttemptRef.current = requestedRecipeId;
      await resumeRecipeConversation(requestedRecipeId);
    };

    void initializeConversations();
    return () => {
      cancelled = true;
    };
  }, [loadConversations, requestedRecipeId, resumeRecipeConversation]);

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
          .querySelector<HTMLInputElement | HTMLTextAreaElement>(
            '#assistant-message'
          )
          ?.focus();
        return;
      }

      if (key === 'n') {
        e.preventDefault();
        handleNewGeneralChat();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNewGeneralChat, hasHydrated]);

  useEffect(() => {
    return () => {
      cancelPendingAssistantReply();
    };
  }, [cancelPendingAssistantReply]);

  useEffect(() => {
    if (!hasHydrated) return;
    if (requestedRecipeId) return;

    if (conversations.length === 0) {
      if (!generalCreationRequestedRef.current) {
        generalCreationRequestedRef.current = true;
        void createConversation();
      }
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
    requestedRecipeId,
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

  const handleBackToRecipe = () => {
    if (!activeRecipeContext) return;

    const origin = locationState?.recipeOrigin;
    const activeRecipePath = `/recipes/${activeRecipeContext.recipeId}`;
    if (origin?.pathname === activeRecipePath) {
      navigate(-1);
      return;
    }

    navigate(activeRecipePath, { replace: true, state: null });
  };

  const handleStartGeneralChat = () => {
    handleNewGeneralChat();
  };

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
          <ConversationList
            onCreateConversation={handleNewGeneralChat}
            onSelectConversation={handleSelectConversation}
          />
        </aside>

        <section
          aria-label="Chat conversation"
          className="flex min-h-0 min-w-0 flex-1 flex-col md:pl-6"
        >
          <header className="max-h-[45dvh] overflow-y-auto pr-1 pb-3 md:max-h-none md:overflow-visible md:pr-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold">SmartMeal Assistant</h1>
                <p className="mt-1 text-sm text-gray-600">
                  Nibble is here to help you plan meals and groceries.
                </p>
              </div>

              <button
                type="button"
                onClick={handleNewGeneralChat}
                className="hidden h-12 rounded-lg border border-gray-300 px-4 text-base font-medium hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 focus:outline-none md:inline-flex"
              >
                New Chat
              </button>
            </div>

            <div className="mt-3 md:hidden" aria-label="Conversation selector">
              <ConversationList
                compact
                onCreateConversation={handleNewGeneralChat}
                onSelectConversation={handleSelectConversation}
              />
            </div>

            {activeRecipeContext ? (
              <div className="mt-3 rounded-lg border border-orange-200 bg-orange-50 p-3">
                <p className="text-sm font-medium text-gray-900">
                  Recipe: {activeRecipeContext.recipeTitle}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleBackToRecipe}
                    className="inline-flex min-h-12 min-w-12 items-center rounded-lg border border-orange-300 bg-white px-4 py-2 text-base font-medium text-gray-900 hover:bg-orange-100 focus:ring-2 focus:ring-orange-500 focus:ring-offset-1 focus:outline-none"
                  >
                    Back to recipe
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      void createRecipeConversation(
                        activeRecipeContext.recipeId
                      )
                    }
                    aria-label={`New conversation for ${activeRecipeContext.recipeTitle}`}
                    className="inline-flex min-h-12 items-center rounded-lg bg-orange-600 px-4 py-2 text-base font-medium text-white hover:bg-orange-700 focus:ring-2 focus:ring-orange-500 focus:ring-offset-1 focus:outline-none"
                  >
                    New recipe chat
                  </button>
                </div>
              </div>
            ) : null}

            {error ? (
              <div
                role="alert"
                className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
              >
                <p>{error}</p>
                {requestedRecipeId && !isRequestedRecipeConversationActive ? (
                  <button
                    type="button"
                    onClick={handleStartGeneralChat}
                    className="mt-2 inline-flex min-h-12 items-center rounded-lg border border-red-300 bg-white px-4 py-2 text-base font-medium text-gray-900 hover:bg-red-100 focus:ring-2 focus:ring-red-500 focus:ring-offset-1 focus:outline-none"
                  >
                    Start a general chat instead
                  </button>
                ) : null}
              </div>
            ) : null}
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
                {hasPreviousMessages ? (
                  <li className="flex justify-center py-1">
                    <button
                      type="button"
                      onClick={() =>
                        activeConversationId &&
                        void loadMoreMessages(activeConversationId)
                      }
                      disabled={isLoading}
                      className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:outline-none disabled:opacity-50"
                    >
                      {isLoading ? 'Loading…' : 'Load older messages'}
                    </button>
                  </li>
                ) : null}
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
            <ChatInput disabled={!isRequestedRecipeConversationActive} />
          </div>
        </section>
      </div>
    </Container>
  );
}
