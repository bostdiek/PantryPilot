import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import {
  acceptAction,
  createRecipeConversation as apiCreateRecipeConversation,
  deleteConversation as apiDeleteConversation,
  cancelAction,
  fetchConversations,
  fetchMessages,
  resumeRecipeConversation as apiResumeRecipeConversation,
  selectRecipeConversation as apiSelectRecipeConversation,
  streamChatMessage,
} from '../api/endpoints/chat';
import { logger } from '../lib/logger';
import {
  classifyTelemetryError,
  createProductTelemetryRequestMetadata,
  emitProductTelemetryEvent,
  getTelemetryLatencyMs,
} from '../lib/telemetry';
import { ApiErrorImpl } from '../types/api';
import type { ChatContentBlock, ConversationSummary } from '../types/Chat';

export type ChatRole = 'user' | 'assistant';

export interface Conversation {
  id: string;
  title: string | null;
  createdAt: string; // ISO
  lastMessageAt: string; // ISO
  isLocalOnly?: boolean;
  recipeContext?: {
    recipeId: string;
    recipeTitle: string;
    isCurrent: boolean;
  };
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
  /** Last selected general conversation, kept separate from recipe context. */
  activeGeneralConversationId: string | null;
  /** Last server-reconciled selection for each recipe. */
  activeRecipeConversationIds: Record<string, string>;
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

  /** Whether there are older messages to load for each conversation */
  hasPreviousMessagesByConversationId: Record<string, boolean>;

  loadConversations: () => Promise<void>;
  loadMessages: (conversationId: string) => Promise<void>;
  loadMoreMessages: (conversationId: string) => Promise<void>;
  createConversation: (title?: string) => Promise<void>;
  resumeRecipeConversation: (recipeId: string) => Promise<void>;
  createRecipeConversation: (recipeId: string) => Promise<void>;
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

const MAX_MESSAGES_PER_CONVERSATION = 200;

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

function toConversation(summary: ConversationSummary): Conversation {
  return {
    id: summary.id,
    title: summary.title,
    createdAt: summary.created_at,
    lastMessageAt: summary.last_activity_at,
    ...(summary.recipe_context
      ? {
          recipeContext: {
            recipeId: summary.recipe_context.recipe_id,
            recipeTitle: summary.recipe_context.recipe_title,
            isCurrent: summary.recipe_context.is_current,
          },
        }
      : {}),
  };
}

function mergeConversationSummary(
  conversations: Conversation[],
  summary: ConversationSummary
): Conversation[] {
  const incoming = toConversation(summary);
  const recipeId = incoming.recipeContext?.recipeId;
  const withoutIncoming = conversations
    .filter((conversation) => conversation.id !== incoming.id)
    .map((conversation) => {
      if (
        recipeId &&
        incoming.recipeContext?.isCurrent &&
        conversation.recipeContext?.recipeId === recipeId
      ) {
        return {
          ...conversation,
          recipeContext: {
            ...conversation.recipeContext,
            isCurrent: false,
          },
        };
      }
      return conversation;
    });

  return [incoming, ...withoutIncoming];
}

function normalizeConversationSummaries(
  summaries: ConversationSummary[]
): Conversation[] {
  return summaries.reduce<Conversation[]>(
    (merged, summary) =>
      mergeConversationSummary(merged, summary).sort(
        (left, right) =>
          Date.parse(right.lastMessageAt) - Date.parse(left.lastMessageAt)
      ),
    []
  );
}

function reconcileLoadedConversationState(
  state: ChatState,
  serverConversations: Conversation[]
): Pick<
  ChatState,
  | 'conversations'
  | 'activeConversationId'
  | 'activeGeneralConversationId'
  | 'activeRecipeConversationIds'
> {
  const activeRecipeConversationIds = Object.fromEntries(
    serverConversations
      .filter(
        (
          conversation
        ): conversation is Conversation & {
          recipeContext: NonNullable<Conversation['recipeContext']>;
        } => conversation.recipeContext?.isCurrent === true
      )
      .map((conversation) => [
        conversation.recipeContext.recipeId,
        conversation.id,
      ])
  );
  const serverConversationIds = new Set(
    serverConversations.map((conversation) => conversation.id)
  );
  const activeLocalGeneralConversation =
    state.activeConversationId === state.activeGeneralConversationId
      ? state.conversations.find(
          (conversation) =>
            conversation.id === state.activeConversationId &&
            conversation.isLocalOnly === true &&
            !conversation.recipeContext
        )
      : undefined;
  const conversations =
    activeLocalGeneralConversation &&
    !serverConversationIds.has(activeLocalGeneralConversation.id)
      ? [activeLocalGeneralConversation, ...serverConversations]
      : serverConversations;
  const conversationIds = new Set(
    conversations.map((conversation) => conversation.id)
  );
  const generalConversationIds = new Set(
    conversations
      .filter((conversation) => !conversation.recipeContext)
      .map((conversation) => conversation.id)
  );

  return {
    conversations,
    activeRecipeConversationIds,
    activeConversationId:
      state.activeConversationId &&
      conversationIds.has(state.activeConversationId)
        ? state.activeConversationId
        : null,
    activeGeneralConversationId:
      state.activeGeneralConversationId &&
      generalConversationIds.has(state.activeGeneralConversationId)
        ? state.activeGeneralConversationId
        : state.activeConversationId &&
            generalConversationIds.has(state.activeConversationId)
          ? state.activeConversationId
          : null,
  };
}

function removeRecipeContextState(
  state: ChatState,
  recipeId: string,
  error: string
): Partial<ChatState> {
  const inaccessibleIds = new Set(
    state.conversations
      .filter(
        (conversation) => conversation.recipeContext?.recipeId === recipeId
      )
      .map((conversation) => conversation.id)
  );
  const messagesByConversationId = { ...state.messagesByConversationId };
  const hasPreviousMessagesByConversationId = {
    ...state.hasPreviousMessagesByConversationId,
  };
  inaccessibleIds.forEach((id) => {
    delete messagesByConversationId[id];
    delete hasPreviousMessagesByConversationId[id];
  });
  const activeRecipeConversationIds = {
    ...state.activeRecipeConversationIds,
  };
  delete activeRecipeConversationIds[recipeId];

  return {
    conversations: state.conversations.filter(
      (conversation) => !inaccessibleIds.has(conversation.id)
    ),
    messagesByConversationId,
    hasPreviousMessagesByConversationId,
    activeRecipeConversationIds,
    // Keep the remembered general selection separate, but do not display it
    // as a success-shaped fallback for a failed contextual open.
    activeConversationId: null,
    error,
  };
}

function isConfirmedInaccessible(error: unknown): boolean {
  return (
    error instanceof ApiErrorImpl &&
    (error.status === 403 || error.status === 404)
  );
}

/**
 * Formats a snake_case tool name into a friendly display string.
 * e.g., "search_recipes" -> "Searching recipes..."
 *       "get_meal_plan_history" -> "Analyzing meal history..."
 */
export function formatToolName(toolName: string): string {
  const toolNameMap: Record<string, string> = {
    get_meal_plan_history: 'Analyzing meal history...',
    search_recipes: 'Searching recipes...',
    get_daily_weather: 'Checking forecast...',
    web_search: 'Searching the web...',
    fetch_url_as_markdown: 'Reading web page...',
    suggest_recipe: 'Creating recipe draft...',
    propose_meal_for_day: 'Proposing meal...',
    update_user_memory: 'Updating memory...',
    final_result: 'Finalizing response...',
  };

  return toolNameMap[toolName] || `Using ${toolName}...`;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      hasHydrated: false,
      conversations: [],
      activeConversationId: null,
      activeGeneralConversationId: null,
      activeRecipeConversationIds: {},
      messagesByConversationId: {},
      hasPreviousMessagesByConversationId: {},
      isLoading: false,
      isStreaming: false,
      streamingMessageId: null,
      error: null,
      _abortController: null,

      loadConversations: async () => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetchConversations();
          const conversations = normalizeConversationSummaries(
            response.conversations
          );
          set((state) =>
            reconcileLoadedConversationState(state, conversations)
          );
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
          const response = await fetchMessages(
            conversationId,
            MAX_MESSAGES_PER_CONVERSATION
          );
          const messages: Message[] = response.messages.map((m) => {
            const blocks = m.content_blocks as ChatContentBlock[];

            // Extract plain text content for user messages (stored as content_blocks with type: "text")
            let content: string | undefined;
            if (
              m.role === 'user' &&
              blocks.length > 0 &&
              blocks[0].type === 'text'
            ) {
              content = blocks[0].text;
            }

            return {
              id: m.id,
              conversationId,
              role: m.role as ChatRole,
              content,
              blocks,
              createdAt: m.created_at,
            };
          });
          set((state) => ({
            messagesByConversationId: {
              ...state.messagesByConversationId,
              [conversationId]: messages,
            },
            hasPreviousMessagesByConversationId: {
              ...state.hasPreviousMessagesByConversationId,
              [conversationId]: response.has_more,
            },
          }));
        } catch (err) {
          logger.error('Failed to load messages:', err);
          set({ error: 'Failed to load messages' });
        } finally {
          set({ isLoading: false });
        }
      },

      loadMoreMessages: async (conversationId: string) => {
        const existingMessages =
          get().messagesByConversationId[conversationId] ?? [];
        if (existingMessages.length === 0) return;

        // Use the oldest message's ID as the cursor
        const oldestMessageId = existingMessages[0].id;

        set({ isLoading: true, error: null });
        try {
          const response = await fetchMessages(
            conversationId,
            MAX_MESSAGES_PER_CONVERSATION,
            oldestMessageId
          );
          const olderMessages: Message[] = response.messages.map((m) => {
            const blocks = m.content_blocks as ChatContentBlock[];

            let content: string | undefined;
            if (
              m.role === 'user' &&
              blocks.length > 0 &&
              blocks[0].type === 'text'
            ) {
              content = blocks[0].text;
            }

            return {
              id: m.id,
              conversationId,
              role: m.role as ChatRole,
              content,
              blocks,
              createdAt: m.created_at,
            };
          });
          set((state) => ({
            messagesByConversationId: {
              ...state.messagesByConversationId,
              [conversationId]: [
                ...olderMessages,
                ...(state.messagesByConversationId[conversationId] ?? []),
              ],
            },
            hasPreviousMessagesByConversationId: {
              ...state.hasPreviousMessagesByConversationId,
              [conversationId]: response.has_more,
            },
          }));
        } catch (err) {
          logger.error('Failed to load older messages:', err);
          set({ error: 'Failed to load older messages' });
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
          isLocalOnly: true,
        };

        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          activeConversationId: newConversation.id,
          activeGeneralConversationId: newConversation.id,
          messagesByConversationId: {
            ...state.messagesByConversationId,
            [newConversation.id]: [],
          },
        }));
      },

      resumeRecipeConversation: async (recipeId: string) => {
        set({ isLoading: true, error: null });
        try {
          // The server is authoritative even when persisted state names a
          // different conversation for this recipe.
          const summary = await apiResumeRecipeConversation(recipeId);
          set((state) => ({
            conversations: mergeConversationSummary(
              state.conversations,
              summary
            ),
            activeConversationId: summary.id,
            activeRecipeConversationIds: {
              ...state.activeRecipeConversationIds,
              [recipeId]: summary.id,
            },
          }));
          await get().loadMessages(summary.id);
        } catch (err) {
          logger.error('Failed to resume recipe conversation:', err);
          if (isConfirmedInaccessible(err)) {
            set((state) =>
              removeRecipeContextState(
                state,
                recipeId,
                'This recipe conversation is no longer available. Return to the recipe and try again.'
              )
            );
          } else {
            set({
              error:
                'Unable to resume this recipe conversation. Please try again.',
            });
          }
        } finally {
          set({ isLoading: false });
        }
      },

      createRecipeConversation: async (recipeId: string) => {
        set({ isLoading: true, error: null });
        try {
          const summary = await apiCreateRecipeConversation(recipeId);
          set((state) => ({
            conversations: mergeConversationSummary(
              state.conversations,
              summary
            ),
            activeConversationId: summary.id,
            activeRecipeConversationIds: {
              ...state.activeRecipeConversationIds,
              [recipeId]: summary.id,
            },
            messagesByConversationId: {
              ...state.messagesByConversationId,
              [summary.id]: [],
            },
            hasPreviousMessagesByConversationId: {
              ...state.hasPreviousMessagesByConversationId,
              [summary.id]: false,
            },
          }));
        } catch (err) {
          logger.error('Failed to create recipe conversation:', err);
          if (isConfirmedInaccessible(err)) {
            set((state) =>
              removeRecipeContextState(
                state,
                recipeId,
                'Unable to create a conversation for this recipe. Return to the recipe and try again.'
              )
            );
          } else {
            set({
              error:
                'Unable to create a conversation for this recipe. Please try again.',
            });
          }
        } finally {
          set({ isLoading: false });
        }
      },

      switchConversation: async (id: string) => {
        const conversation = get().conversations.find(
          (candidate) => candidate.id === id
        );
        const recipeId = conversation?.recipeContext?.recipeId;

        if (recipeId) {
          set({ isLoading: true, error: null });
          try {
            // Selecting contextual history is a server mutation and must
            // complete before its messages become active.
            const summary = await apiSelectRecipeConversation(id);
            set((state) => ({
              conversations: mergeConversationSummary(
                state.conversations,
                summary
              ),
              activeConversationId: summary.id,
              activeRecipeConversationIds: {
                ...state.activeRecipeConversationIds,
                [recipeId]: summary.id,
              },
            }));
          } catch (err) {
            logger.error('Failed to select recipe conversation:', err);
            if (isConfirmedInaccessible(err)) {
              set((state) =>
                removeRecipeContextState(
                  state,
                  recipeId,
                  'This recipe conversation is no longer available. Return to the recipe and try again.'
                )
              );
            } else {
              set({
                error:
                  'Unable to select this recipe conversation. Please try again.',
              });
            }
            return;
          } finally {
            set({ isLoading: false });
          }
        } else {
          set({
            activeConversationId: id,
            activeGeneralConversationId: id,
            error: null,
          });
        }
        // Always reload from server to ensure consistency across devices.
        // Cached messages remain visible while the fresh load completes.
        await get().loadMessages(id);
      },

      deleteConversation: async (id: string) => {
        set({ isLoading: true, error: null });
        let deletedOnServer = false;
        const deletedConversation = get().conversations.find(
          (conversation) => conversation.id === id
        );
        const deletedRecipeId = deletedConversation?.recipeContext?.recipeId;
        const wasActive = get().activeConversationId === id;
        try {
          await apiDeleteConversation(id);
          deletedOnServer = true;

          if (deletedRecipeId) {
            const response = await fetchConversations();
            const conversations = normalizeConversationSummaries(
              response.conversations
            );
            const currentRecipeConversation = conversations.find(
              (conversation) =>
                conversation.recipeContext?.recipeId === deletedRecipeId &&
                conversation.recipeContext.isCurrent
            );

            set((state) => {
              const reconciled = reconcileLoadedConversationState(
                state,
                conversations
              );
              const { [id]: _removedMessages, ...messagesByConversationId } =
                state.messagesByConversationId;
              const {
                [id]: _removedPagination,
                ...hasPreviousMessagesByConversationId
              } = state.hasPreviousMessagesByConversationId;

              return {
                ...reconciled,
                activeConversationId: wasActive
                  ? (currentRecipeConversation?.id ?? null)
                  : reconciled.activeConversationId,
                messagesByConversationId,
                hasPreviousMessagesByConversationId,
              };
            });

            if (wasActive) {
              if (currentRecipeConversation) {
                await get().loadMessages(currentRecipeConversation.id);
              } else {
                await get().createRecipeConversation(deletedRecipeId);
              }
            }
            return;
          }

          let nextActiveConversationId: string | null = null;
          let shouldCreateGeneralConversation = false;
          set((state) => {
            const updatedConversations = state.conversations.filter(
              (c) => c.id !== id
            );
            const remainingGeneralConversation =
              updatedConversations.find(
                (conversation) => !conversation.recipeContext
              ) ?? null;
            const { [id]: _removedMessages, ...messagesByConversationId } =
              state.messagesByConversationId;
            const {
              [id]: _removedPagination,
              ...hasPreviousMessagesByConversationId
            } = state.hasPreviousMessagesByConversationId;
            const activeGeneralConversationId =
              state.activeGeneralConversationId === id
                ? (remainingGeneralConversation?.id ?? null)
                : state.activeGeneralConversationId;
            nextActiveConversationId =
              state.activeConversationId === id
                ? activeGeneralConversationId
                : state.activeConversationId;
            shouldCreateGeneralConversation =
              state.activeConversationId === id &&
              nextActiveConversationId === null;

            return {
              conversations: updatedConversations,
              messagesByConversationId,
              hasPreviousMessagesByConversationId,
              activeConversationId: nextActiveConversationId,
              activeGeneralConversationId,
            };
          });

          if (shouldCreateGeneralConversation) {
            await get().createConversation();
          }
        } catch (err) {
          logger.error('Failed to delete conversation:', err);
          if (deletedOnServer && deletedRecipeId) {
            set((state) =>
              removeRecipeContextState(
                state,
                deletedRecipeId,
                'The conversation was deleted, but recipe conversations could not be refreshed. Return to the recipe and try again.'
              )
            );
            return;
          }
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
        const requestTelemetry = createProductTelemetryRequestMetadata({
          featureName: 'assistant',
          conversationId,
        });
        const streamStartedAt = Date.now();
        const startedToolNames: string[] = [];
        let streamCompleted = false;
        let streamErrored = false;
        let streamCancelled = false;

        emitProductTelemetryEvent(
          'assistant_message_started',
          requestTelemetry,
          {
            streamed: true,
            success: true,
          }
        );

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
        let serverMessageId: string | undefined;
        const finalizeStreamingState = (options?: {
          errorDetail?: string;
          clearError?: boolean;
          messageId?: string;
        }) => {
          set((state) => {
            const messages =
              state.messagesByConversationId[conversationId] ?? [];
            const targetMessageId = options?.messageId ?? serverMessageId;
            const updatedMessages = messages.map((message) => {
              if (
                message.id === assistantMessageId ||
                (targetMessageId && message.id === targetMessageId)
              ) {
                const hasContent =
                  (message.blocks && message.blocks.length > 0) ||
                  accumulatedText.length > 0;

                if (options?.errorDetail && !hasContent) {
                  const errorBlock: ChatContentBlock = {
                    type: 'text',
                    text: `Sorry, I encountered an error: ${options.errorDetail}`,
                  };
                  return {
                    ...message,
                    blocks: [errorBlock],
                    isStreaming: false,
                    statusText: undefined,
                  };
                }

                return {
                  ...message,
                  isStreaming: false,
                  statusText: undefined,
                };
              }

              return message;
            });

            return {
              isLoading: false,
              isStreaming: false,
              streamingMessageId: null,
              _abortController: null,
              error:
                options?.errorDetail ??
                (options?.clearError ? null : state.error),
              messagesByConversationId: {
                ...state.messagesByConversationId,
                [conversationId]: updatedMessages,
              },
            };
          });
        };

        // Create and expose the AbortController before streaming begins so
        // cancelPendingAssistantReply() can abort the in-flight request.
        const storeAbortController = new AbortController();
        storeAbortController.signal.addEventListener(
          'abort',
          () => {
            streamCancelled = true;
            if (!streamCompleted && !streamErrored) {
              emitProductTelemetryEvent(
                'assistant_message_failed',
                requestTelemetry,
                {
                  success: false,
                  cancelled: true,
                  streamed: true,
                  latency_ms: getTelemetryLatencyMs(streamStartedAt),
                  error_type: 'cancelled',
                  tool_count: startedToolNames.length,
                  tool_names: startedToolNames.slice(0, 10),
                }
              );
            }
          },
          { once: true }
        );
        set({ _abortController: storeAbortController });

        // Stream the response
        // Get the conversation title to pass to backend for new conversations
        const conversation = get().conversations.find(
          (c) => c.id === conversationId
        );
        await streamChatMessage(
          conversationId,
          trimmed,
          {
            onDelta: (delta, messageId) => {
              accumulatedText += delta;
              if (messageId && !serverMessageId) {
                serverMessageId = messageId;
              }
              set((state) => {
                const messages =
                  state.messagesByConversationId[conversationId] ?? [];
                const updatedMessages = messages.map((m) => {
                  if (m.id === assistantMessageId || m.id === messageId) {
                    // Update text block while preserving non-text blocks
                    // (recipe cards, meal proposals, etc. added via blocks.append)
                    const textBlock: ChatContentBlock = {
                      type: 'text',
                      text: accumulatedText,
                    };
                    const existingNonTextBlocks = (m.blocks ?? []).filter(
                      (b) => b.type !== 'text'
                    );
                    return {
                      ...m,
                      id: messageId || m.id,
                      blocks: [textBlock, ...existingNonTextBlocks],
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
              if (messageId && !serverMessageId) {
                serverMessageId = messageId;
              }
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
              if (!streamCompleted && !streamErrored && !streamCancelled) {
                streamCompleted = true;
                emitProductTelemetryEvent(
                  'assistant_message_completed',
                  requestTelemetry,
                  {
                    success: true,
                    latency_ms: getTelemetryLatencyMs(streamStartedAt),
                    streamed: true,
                    tool_count: startedToolNames.length,
                    tool_names: startedToolNames.slice(0, 10),
                  }
                );
              }
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
              if (!streamErrored && !streamCancelled) {
                streamErrored = true;
                emitProductTelemetryEvent(
                  'assistant_message_failed',
                  requestTelemetry,
                  {
                    success: false,
                    streamed: true,
                    latency_ms: getTelemetryLatencyMs(streamStartedAt),
                    error_type:
                      errorCode || classifyTelemetryError(new Error(detail)),
                    tool_count: startedToolNames.length,
                    tool_names: startedToolNames.slice(0, 10),
                  }
                );
              }
              finalizeStreamingState({ errorDetail: detail });
            },

            onDone: () => {
              if (!streamCompleted && !streamErrored && !streamCancelled) {
                streamCompleted = true;
                emitProductTelemetryEvent(
                  'assistant_message_completed',
                  requestTelemetry,
                  {
                    success: true,
                    streamed: true,
                    latency_ms: getTelemetryLatencyMs(streamStartedAt),
                    tool_count: startedToolNames.length,
                    tool_names: startedToolNames.slice(0, 10),
                  }
                );
              }
              finalizeStreamingState({ clearError: true });
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
              startedToolNames.push(toolName);
              if (toolName === 'search_recipes' || toolName === 'web_search') {
                emitProductTelemetryEvent(
                  'recipe_search_submitted',
                  requestTelemetry,
                  {
                    success: true,
                    streamed: true,
                    tool_names: [toolName],
                    tool_count: 1,
                  }
                );
              }
              emitProductTelemetryEvent(
                'assistant_tool_started',
                requestTelemetry,
                {
                  success: true,
                  tool_names: [toolName],
                  tool_count: 1,
                }
              );
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
              const rawToolName = data.tool_name;
              const toolName =
                typeof rawToolName === 'string' ? rawToolName : undefined;
              emitProductTelemetryEvent(
                'assistant_tool_completed',
                requestTelemetry,
                {
                  success: true,
                  tool_names: toolName ? [toolName] : undefined,
                  tool_count: toolName ? 1 : undefined,
                }
              );
            },
          },
          conversation?.title || undefined,
          requestTelemetry,
          storeAbortController.signal
        );

        if (!streamCompleted && !streamErrored) {
          if (streamCancelled) {
            finalizeStreamingState({ clearError: true });
          } else {
            streamErrored = true;
            emitProductTelemetryEvent(
              'assistant_message_failed',
              requestTelemetry,
              {
                success: false,
                streamed: true,
                latency_ms: getTelemetryLatencyMs(streamStartedAt),
                error_type: 'stream_terminated',
                tool_count: startedToolNames.length,
                tool_names: startedToolNames.slice(0, 10),
              }
            );
            finalizeStreamingState({
              errorDetail:
                'The assistant connection closed unexpectedly. Please try again.',
            });
          }
        }
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
        activeGeneralConversationId: state.activeGeneralConversationId,
        activeRecipeConversationIds: state.activeRecipeConversationIds,
        messagesByConversationId: state.messagesByConversationId,
        hasPreviousMessagesByConversationId:
          state.hasPreviousMessagesByConversationId,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.hasHydrated = true;
        }
      },
    }
  )
);
