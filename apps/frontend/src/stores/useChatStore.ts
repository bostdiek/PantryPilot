import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import {
  acceptAction,
  deleteConversation as apiDeleteConversation,
  cancelAction,
  fetchConversations,
  fetchMessages,
  streamChatMessage,
} from '../api/endpoints/chat';
import { logger } from '../lib/logger';
import type { ChatContentBlock } from '../types/Chat';

export type ChatRole = 'user' | 'assistant';

export interface Conversation {
  id: string;
  title: string | null;
  createdAt: string; // ISO
  lastMessageAt: string; // ISO
}

export interface Message {
  id: string;
  conversationId: string;
  role: ChatRole;
  /** Plain text content (for user messages) */
  content?: string;
  /** Structured content blocks (for assistant messages) */
  blocks?: ChatContentBlock[];
  createdAt: string; // ISO
  /** Whether the message is currently being streamed */
  isStreaming?: boolean;
  /** Current status text to show during streaming (e.g., "Searching recipes...") */
  statusText?: string;
}

export interface ChatState {
  hasHydrated: boolean;
  conversations: Conversation[];
  activeConversationId: string | null;
  messagesByConversationId: Record<string, Message[]>;
  isLoading: boolean;
  /** Whether an assistant response is currently streaming */
  isStreaming: boolean;
  /** ID of the message currently being streamed */
  streamingMessageId: string | null;
  /** Current error message, if any */
  error: string | null;
  /** AbortController for canceling the current stream */
  _abortController: AbortController | null;

  loadConversations: () => Promise<void>;
  loadMessages: (conversationId: string) => Promise<void>;
  createConversation: (title?: string) => Promise<void>;
  switchConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  cancelPendingAssistantReply: () => void;
  clearConversation: (id: string) => void;
  acceptAction: (actionId: string) => Promise<void>;
  cancelAction: (actionId: string) => Promise<void>;
  appendLocalAssistantMessage: (text: string, conversationId?: string) => void;
  clearError: () => void;
}

const MAX_MESSAGES_PER_CONVERSATION = 50;

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

/**
 * Formats a snake_case tool name into a friendly display string.
 * e.g., "search_recipes" -> "Searching recipes..."
 *       "get_user_preferences" -> "Getting user preferences..."
 */
function formatToolName(toolName: string): string {
  // Map of known tool names to friendly descriptions
  const toolNameMap: Record<string, string> = {
    search_recipes: 'Searching recipes...',
    get_recipe: 'Fetching recipe details...',
    get_recipes: 'Fetching recipes...',
    search_web: 'Searching the web...',
    get_user_preferences: 'Checking your preferences...',
    get_meal_plan: 'Loading meal plan...',
    create_meal_plan: 'Creating meal plan...',
    add_to_meal_plan: 'Adding to meal plan...',
    get_grocery_list: 'Generating grocery list...',
  };

  if (toolNameMap[toolName]) {
    return toolNameMap[toolName];
  }

  // Fallback: convert snake_case to sentence case with "..."
  const words = toolName.split('_');
  const firstWord = words[0];
  const rest = words.slice(1).join(' ');
  // Capitalize first letter and add -ing suffix if it looks like a verb
  const capitalized =
    firstWord.charAt(0).toUpperCase() + firstWord.slice(1) + 'ing';
  return `${capitalized} ${rest}...`.trim();
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      hasHydrated: false,
      conversations: [],
      activeConversationId: null,
      messagesByConversationId: {},
      isLoading: false,
      isStreaming: false,
      streamingMessageId: null,
      error: null,
      _abortController: null,

      loadConversations: async () => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetchConversations();
          const conversations: Conversation[] = response.conversations.map(
            (c) => ({
              id: c.id,
              title: c.title,
              createdAt: c.created_at,
              lastMessageAt: c.last_activity_at,
            })
          );
          set({ conversations });
        } catch (err) {
          logger.error('Failed to load conversations:', err);
          set({ error: 'Failed to load conversations' });
        } finally {
          set({ isLoading: false });
        }
      },

      loadMessages: async (conversationId: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetchMessages(conversationId);
          const messages: Message[] = response.messages.map((m) => ({
            id: m.id,
            conversationId,
            role: m.role as ChatRole,
            blocks: m.content_blocks as ChatContentBlock[],
            createdAt: m.created_at,
          }));
          set((state) => ({
            messagesByConversationId: {
              ...state.messagesByConversationId,
              [conversationId]: messages,
            },
          }));
        } catch (err) {
          logger.error('Failed to load messages:', err);
          set({ error: 'Failed to load messages' });
        } finally {
          set({ isLoading: false });
        }
      },

      createConversation: async (title?: string) => {
        // Create a local conversation optimistically
        // The backend will create the real one on first message
        const now = getNowIso();

        // Generate title with user's local timezone if not provided
        const conversationTitle =
          title ||
          new Intl.DateTimeFormat(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
          }).format(new Date());

        const newConversation: Conversation = {
          id: createId(),
          title: conversationTitle,
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
        set({ activeConversationId: id, error: null });
        // Load messages for this conversation if not already loaded
        const messages = get().messagesByConversationId[id];
        if (!messages || messages.length === 0) {
          await get().loadMessages(id);
        }
      },

      deleteConversation: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
          // Call API to delete the conversation
          await apiDeleteConversation(id);

          // Remove conversation from local state
          set((state) => {
            const updatedConversations = state.conversations.filter(
              (c) => c.id !== id
            );

            // Remove messages for this conversation
            const { [id]: _removed, ...remainingMessages } =
              state.messagesByConversationId;

            // If the deleted conversation was active, switch to another one or create new
            let newActiveId = state.activeConversationId;
            if (state.activeConversationId === id) {
              if (updatedConversations.length > 0) {
                // Switch to the most recent conversation
                newActiveId = updatedConversations[0].id;
              } else {
                // No conversations left, will create a new one
                newActiveId = null;
              }
            }

            return {
              conversations: updatedConversations,
              messagesByConversationId: remainingMessages,
              activeConversationId: newActiveId,
            };
          });

          // If there were no conversations left, create a new one
          if (get().conversations.length === 0) {
            await get().createConversation();
          }
        } catch (err) {
          logger.error('Failed to delete conversation:', err);
          set({ error: 'Failed to delete conversation' });
          throw err;
        } finally {
          set({ isLoading: false });
        }
      },

      sendMessage: async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed) return;

        // Cancel any pending stream
        const existingAbort = get()._abortController;
        if (existingAbort) {
          existingAbort.abort();
        }

        // Create conversation if needed
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

        // Create placeholder for assistant response
        const assistantMessageId = createId();
        const assistantMessage: Message = {
          id: assistantMessageId,
          conversationId,
          role: 'assistant',
          blocks: [],
          createdAt: now,
          isStreaming: true,
        };

        set((state) => {
          const nextMessages = capMessages([
            ...(state.messagesByConversationId[conversationId] ?? []),
            userMessage,
            assistantMessage,
          ]);

          return {
            isLoading: true,
            isStreaming: true,
            streamingMessageId: assistantMessageId,
            error: null,
            messagesByConversationId: {
              ...state.messagesByConversationId,
              [conversationId]: nextMessages,
            },
            conversations: state.conversations.map((c) =>
              c.id === conversationId ? { ...c, lastMessageAt: now } : c
            ),
          };
        });

        // Accumulated text for building TextBlock
        let accumulatedText = '';

        // Stream the response
        // Get the conversation title to pass to backend for new conversations
        const conversation = get().conversations.find(
          (c) => c.id === conversationId
        );
        const abortController = await streamChatMessage(
          conversationId,
          trimmed,
          {
            onDelta: (delta, messageId) => {
              accumulatedText += delta;
              set((state) => {
                const messages =
                  state.messagesByConversationId[conversationId] ?? [];
                const updatedMessages = messages.map((m) => {
                  if (m.id === assistantMessageId || m.id === messageId) {
                    // Update blocks with accumulated text
                    const textBlock: ChatContentBlock = {
                      type: 'text',
                      text: accumulatedText,
                    };
                    return {
                      ...m,
                      id: messageId || m.id,
                      blocks: [textBlock],
                      isStreaming: true,
                    };
                  }
                  return m;
                });
                return {
                  messagesByConversationId: {
                    ...state.messagesByConversationId,
                    [conversationId]: updatedMessages,
                  },
                };
              });
            },

            onBlocksAppend: (blocks, messageId) => {
              set((state) => {
                const messages =
                  state.messagesByConversationId[conversationId] ?? [];
                const updatedMessages = messages.map((m) => {
                  if (m.id === assistantMessageId || m.id === messageId) {
                    return {
                      ...m,
                      id: messageId || m.id,
                      blocks: [...(m.blocks ?? []), ...blocks],
                      isStreaming: true,
                    };
                  }
                  return m;
                });
                return {
                  messagesByConversationId: {
                    ...state.messagesByConversationId,
                    [conversationId]: updatedMessages,
                  },
                };
              });
            },

            onComplete: (messageId) => {
              set((state) => {
                const messages =
                  state.messagesByConversationId[conversationId] ?? [];
                const updatedMessages = messages.map((m) => {
                  if (m.id === assistantMessageId || m.id === messageId) {
                    return {
                      ...m,
                      id: messageId || m.id,
                      isStreaming: false,
                    };
                  }
                  return m;
                });
                return {
                  isStreaming: false,
                  streamingMessageId: null,
                  messagesByConversationId: {
                    ...state.messagesByConversationId,
                    [conversationId]: updatedMessages,
                  },
                };
              });
            },

            onError: (errorCode, detail) => {
              logger.error(`Chat stream error: ${errorCode} - ${detail}`);
              set((state) => {
                const messages =
                  state.messagesByConversationId[conversationId] ?? [];
                const updatedMessages = messages.map((m) => {
                  if (m.id === assistantMessageId) {
                    // Keep partial content if any, mark as not streaming
                    const hasContent =
                      (m.blocks && m.blocks.length > 0) ||
                      accumulatedText.length > 0;
                    if (!hasContent) {
                      // Add error block
                      const errorBlock: ChatContentBlock = {
                        type: 'text',
                        text: `Sorry, I encountered an error: ${detail}`,
                      };
                      return {
                        ...m,
                        blocks: [errorBlock],
                        isStreaming: false,
                      };
                    }
                    return { ...m, isStreaming: false };
                  }
                  return m;
                });
                return {
                  isLoading: false,
                  isStreaming: false,
                  streamingMessageId: null,
                  error: detail,
                  messagesByConversationId: {
                    ...state.messagesByConversationId,
                    [conversationId]: updatedMessages,
                  },
                };
              });
            },

            onDone: () => {
              set({
                isLoading: false,
                isStreaming: false,
                streamingMessageId: null,
                _abortController: null,
              });
            },

            onStatus: (status, detail) => {
              logger.debug(`Chat status: ${status} - ${detail ?? ''}`);
              // Update the streaming message's status text
              const conversationId = get().activeConversationId;
              const streamingMsgId = get().streamingMessageId;
              if (conversationId && streamingMsgId) {
                set((state) => {
                  const messages =
                    state.messagesByConversationId[conversationId] ?? [];
                  const updatedMessages = messages.map((m) =>
                    m.id === streamingMsgId
                      ? { ...m, statusText: detail ?? status }
                      : m
                  );
                  return {
                    messagesByConversationId: {
                      ...state.messagesByConversationId,
                      [conversationId]: updatedMessages,
                    },
                  };
                });
              }
            },

            onToolStarted: (toolName, data) => {
              logger.debug(`Tool started: ${toolName}`, data);
              // Show tool name as status
              const conversationId = get().activeConversationId;
              const streamingMsgId = get().streamingMessageId;
              if (conversationId && streamingMsgId) {
                // Format tool name nicely (e.g., search_recipes -> Searching recipes)
                const friendlyName = formatToolName(toolName);
                set((state) => {
                  const messages =
                    state.messagesByConversationId[conversationId] ?? [];
                  const updatedMessages = messages.map((m) =>
                    m.id === streamingMsgId
                      ? { ...m, statusText: friendlyName }
                      : m
                  );
                  return {
                    messagesByConversationId: {
                      ...state.messagesByConversationId,
                      [conversationId]: updatedMessages,
                    },
                  };
                });
              }
            },

            onToolProposed: (proposalId, data) => {
              logger.debug(`Tool proposed: ${proposalId}`, data);
            },

            onToolResult: (data) => {
              logger.debug('Tool result:', data);
            },
          },
          conversation?.title || undefined
        );

        set({ _abortController: abortController });
      },

      cancelPendingAssistantReply: () => {
        const abortController = get()._abortController;
        if (abortController) {
          abortController.abort();
        }

        const conversationId = get().activeConversationId;
        const streamingMessageId = get().streamingMessageId;

        if (conversationId && streamingMessageId) {
          set((state) => {
            const messages =
              state.messagesByConversationId[conversationId] ?? [];
            const updatedMessages = messages.map((m) => {
              if (m.id === streamingMessageId) {
                return { ...m, isStreaming: false };
              }
              return m;
            });
            return {
              messagesByConversationId: {
                ...state.messagesByConversationId,
                [conversationId]: updatedMessages,
              },
            };
          });
        }

        set({
          isLoading: false,
          isStreaming: false,
          streamingMessageId: null,
          _abortController: null,
        });
      },

      clearConversation: (id: string) => {
        set((state) => ({
          messagesByConversationId: {
            ...state.messagesByConversationId,
            [id]: [],
          },
        }));
      },

      acceptAction: async (actionId: string) => {
        try {
          await acceptAction(actionId);
        } catch (err) {
          logger.error('Failed to accept action:', err);
          throw err;
        }
      },

      cancelAction: async (actionId: string) => {
        try {
          await cancelAction(actionId);
        } catch (err) {
          logger.error('Failed to cancel action:', err);
          throw err;
        }
      },

      appendLocalAssistantMessage: (
        text: string,
        conversationIdOverride?: string
      ) => {
        const trimmed = text.trim();
        if (!trimmed) return;

        const conversationId =
          conversationIdOverride ?? get().activeConversationId;
        if (!conversationId) return;

        // Only append if the conversation exists locally.
        // (This prevents creating messages for unknown/expired conversation IDs.)
        const conversationExists = get().conversations.some(
          (conversation) => conversation.id === conversationId
        );
        if (!conversationExists) return;

        const now = getNowIso();
        const message: Message = {
          id: createId(),
          conversationId,
          role: 'assistant',
          blocks: [{ type: 'text', text: trimmed }],
          createdAt: now,
        };

        set((state) => {
          const nextMessages = capMessages([
            ...(state.messagesByConversationId[conversationId] ?? []),
            message,
          ]);

          return {
            messagesByConversationId: {
              ...state.messagesByConversationId,
              [conversationId]: nextMessages,
            },
            conversations: state.conversations.map((c) =>
              c.id === conversationId ? { ...c, lastMessageAt: now } : c
            ),
          };
        });
      },

      clearError: () => {
        set({ error: null });
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
