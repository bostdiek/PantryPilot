import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ChatRole = 'user' | 'assistant';

export interface Conversation {
  id: string;
  title: string;
  createdAt: string; // ISO
  lastMessageAt: string; // ISO
}

export interface Message {
  id: string;
  conversationId: string;
  role: ChatRole;
  content: string;
  createdAt: string; // ISO
}

export interface ChatState {
  hasHydrated: boolean;
  conversations: Conversation[];
  activeConversationId: string | null;
  messagesByConversationId: Record<string, Message[]>;
  isLoading: boolean;

  loadConversations: () => Promise<void>;
  createConversation: (title?: string) => Promise<void>;
  switchConversation: (id: string) => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  cancelPendingAssistantReply: () => void;
  clearConversation: (id: string) => void;
}

const MAX_MESSAGES_PER_CONVERSATION = 50;

let pendingAssistantReplyTimeoutId: ReturnType<typeof setTimeout> | null = null;

function getNowIso(): string {
  return new Date().toISOString();
}

function createId(): string {
  const maybeId = globalThis.crypto?.randomUUID?.();
  if (maybeId) return maybeId;

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function capMessages(messages: Message[]): Message[] {
  if (messages.length <= MAX_MESSAGES_PER_CONVERSATION) return messages;
  return messages.slice(-MAX_MESSAGES_PER_CONVERSATION);
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      hasHydrated: false,
      conversations: [],
      activeConversationId: null,
      messagesByConversationId: {},
      isLoading: false,

      loadConversations: async () => {
        set({ isLoading: true });
        try {
          // Story 1 is frontend-only; backend integration comes in Story 2.
          // This is intentionally a no-op for now.
          return;
        } finally {
          set({ isLoading: false });
        }
      },

      createConversation: async (title = 'Chat with Nibble') => {
        const now = getNowIso();
        const newConversation: Conversation = {
          id: createId(),
          title,
          createdAt: now,
          lastMessageAt: now,
        };

        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          activeConversationId: newConversation.id,
          messagesByConversationId: {
            ...state.messagesByConversationId,
            [newConversation.id]: [],
          },
        }));
      },

      switchConversation: async (id: string) => {
        set({ activeConversationId: id });
      },

      sendMessage: async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed) return;

        if (pendingAssistantReplyTimeoutId) {
          clearTimeout(pendingAssistantReplyTimeoutId);
          pendingAssistantReplyTimeoutId = null;
        }

        if (!get().activeConversationId) {
          await get().createConversation();
        }

        const conversationId = get().activeConversationId;
        if (!conversationId) return;

        const now = getNowIso();
        const userMessage: Message = {
          id: createId(),
          conversationId,
          role: 'user',
          content: trimmed,
          createdAt: now,
        };

        set((state) => {
          const nextMessages = capMessages([
            ...(state.messagesByConversationId[conversationId] ?? []),
            userMessage,
          ]);

          return {
            isLoading: true,
            messagesByConversationId: {
              ...state.messagesByConversationId,
              [conversationId]: nextMessages,
            },
            conversations: state.conversations.map((c) =>
              c.id === conversationId ? { ...c, lastMessageAt: now } : c
            ),
          };
        });

        pendingAssistantReplyTimeoutId = setTimeout(() => {
          pendingAssistantReplyTimeoutId = null;
          const assistantNow = getNowIso();
          const assistantMessage: Message = {
            id: createId(),
            conversationId,
            role: 'assistant',
            content:
              "I'm Nibble — backend integration is coming soon. For now, I can help with mock meal ideas and grocery list starters.",
            createdAt: assistantNow,
          };

          set((state) => {
            const nextMessages = capMessages([
              ...(state.messagesByConversationId[conversationId] ?? []),
              assistantMessage,
            ]);

            return {
              isLoading: false,
              messagesByConversationId: {
                ...state.messagesByConversationId,
                [conversationId]: nextMessages,
              },
              conversations: state.conversations.map((c) =>
                c.id === conversationId
                  ? { ...c, lastMessageAt: assistantNow }
                  : c
              ),
            };
          });
        }, 700);
      },

      cancelPendingAssistantReply: () => {
        if (pendingAssistantReplyTimeoutId) {
          clearTimeout(pendingAssistantReplyTimeoutId);
          pendingAssistantReplyTimeoutId = null;
        }

        // If we were showing typing state, ensure it stops when cancelled.
        set({ isLoading: false });
      },

      clearConversation: (id: string) => {
        set((state) => ({
          messagesByConversationId: {
            ...state.messagesByConversationId,
            [id]: [],
          },
        }));
      },
    }),
    {
      name: 'chat',
      partialize: (state) => ({
        conversations: state.conversations,
        activeConversationId: state.activeConversationId,
        messagesByConversationId: state.messagesByConversationId,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.hasHydrated = true;
        }
      },
    }
  )
);
