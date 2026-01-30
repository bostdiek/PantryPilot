/**
 * Chat TypeScript types matching backend schemas.
 *
 * These types mirror the Pydantic models in:
 * - apps/backend/src/schemas/chat_content.py
 * - apps/backend/src/schemas/chat_streaming.py
 */

// -----------------------------------------------------------------------------
// Content Block Types
// -----------------------------------------------------------------------------

/**
 * Plain text block - supports markdown rendering.
 */
export interface TextBlock {
  type: 'text';
  text: string;
}

/**
 * Clickable link block with label and URL.
 */
export interface LinkBlock {
  type: 'link';
  label: string;
  href: string;
}

/**
 * Recipe card block with optional deep link.
 *
 * For AI-suggested recipes:
 * - href: Internal draft approval link (/recipes/new?ai=1&...)
 * - source_url: Original external recipe URL for viewing
 */
export interface RecipeCardBlock {
  type: 'recipe_card';
  recipe_id: string | null;
  title: string;
  subtitle: string | null;
  image_url: string | null;
  href: string | null;
  source_url: string | null;
}

/**
 * UI action block that may require confirmation.
 */
export interface ActionBlock {
  type: 'action';
  action_id: string;
  label: string;
  requires_confirmation: boolean;
}

/**
 * Reference to a recipe in user's collection.
 */
export interface ExistingRecipeOption {
  id: string;
  title: string;
  image_url?: string | null;
  detail_path?: string | null;
}

/**
 * Reference to a new recipe from web search.
 */
export interface NewRecipeOption {
  title: string;
  source_url: string;
  description?: string | null;
}

/**
 * Meal plan proposal block for a specific day.
 *
 * Used during meal planning conversations to present recipe options
 * with Accept/Reject functionality. Does not automatically add to
 * meal plan; requires user acceptance.
 */
export interface MealProposalBlock {
  type: 'meal_proposal';
  proposal_id: string; // For tracking accept/reject (e.g., "2026-01-26-proposal")
  date: string; // ISO date (YYYY-MM-DD)
  day_label: string; // Human-friendly day name ("Monday", "Taco Tuesday", etc.)
  existing_recipe?: ExistingRecipeOption | null;
  new_recipe?: NewRecipeOption | null;
  is_leftover?: boolean;
  is_eating_out?: boolean;
  notes?: string | null;
}

/**
 * Discriminated union of all content block types.
 * Use `block.type` to discriminate between variants.
 */
export type ChatContentBlock =
  | TextBlock
  | LinkBlock
  | RecipeCardBlock
  | ActionBlock
  | MealProposalBlock;

// -----------------------------------------------------------------------------
// SSE Event Types
// -----------------------------------------------------------------------------

/**
 * All possible SSE event types from the chat streaming endpoint.
 */
export type ChatSseEventType =
  | 'status'
  | 'message.delta'
  | 'message.complete'
  | 'blocks.append'
  | 'tool.started'
  | 'tool.proposed'
  | 'tool.canceled'
  | 'tool.result'
  | 'memory.updated'
  | 'summary.updated'
  | 'error'
  | 'done';

/**
 * SSE event envelope for chat assistant streaming.
 * The `data` field contains event-specific payload.
 */
export interface ChatSseEvent {
  event: ChatSseEventType;
  conversation_id: string;
  message_id: string | null;
  data: Record<string, unknown>;
}

/**
 * Typed data payloads for specific SSE events.
 */
export interface ChatSseStatusData {
  status: string;
  detail?: string;
}

export interface ChatSseDeltaData {
  delta: string;
}

export interface ChatSseBlocksAppendData {
  blocks: ChatContentBlock[];
}

export interface ChatSseErrorData {
  error_code: string;
  detail: string;
}

// -----------------------------------------------------------------------------
// Message and Conversation Types
// -----------------------------------------------------------------------------

export type ChatRole = 'user' | 'assistant';

/**
 * User feedback on AI assistant responses for training data quality signals.
 */
export type UserFeedback = 'positive' | 'negative' | null;

/**
 * Assistant message composed of canonical content blocks.
 */
export interface AssistantMessage {
  blocks: ChatContentBlock[];
}

/**
 * Frontend message type supporting both plain text (user) and blocks (assistant).
 */
export interface ChatMessage {
  id: string;
  conversationId: string;
  role: ChatRole;
  /** For user messages: plain text content */
  content?: string;
  /** For assistant messages: structured content blocks */
  blocks?: ChatContentBlock[];
  createdAt: string; // ISO 8601
}

/**
 * Conversation summary for list views.
 * Matches backend ConversationSummary schema.
 */
export interface Conversation {
  id: string;
  title: string | null;
  createdAt: string; // ISO 8601
  lastActivityAt: string; // ISO 8601
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

/**
 * Response for listing user conversations.
 * Matches backend ConversationListResponse schema.
 */
export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
  has_more: boolean;
}

/**
 * Conversation summary from backend.
 * Uses snake_case to match backend JSON serialization.
 */
export interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  last_activity_at: string;
}

/**
 * Message summary from backend.
 * Uses snake_case to match backend JSON serialization.
 */
export interface MessageSummary {
  id: string;
  role: string;
  content_blocks: ChatContentBlock[];
  created_at: string;
}

/**
 * Response for fetching message history.
 * Matches backend MessageHistoryResponse schema.
 */
export interface MessageHistoryResponse {
  messages: MessageSummary[];
  has_more: boolean;
}

// -----------------------------------------------------------------------------
// Request Types
// -----------------------------------------------------------------------------

/**
 * Request payload for streaming a chat assistant response.
 * Matches backend ChatStreamRequest schema.
 */
export interface ChatStreamRequest {
  content: string;
  client_context?: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// Action API Types
// -----------------------------------------------------------------------------

/**
 * Request payload for accepting an action.
 */
export interface AcceptActionRequest {
  confirmed: boolean;
}

/**
 * Response from action accept/cancel endpoints.
 */
export interface ActionResponse {
  success: boolean;
  action_id: string;
  status: 'accepted' | 'canceled' | 'pending';
  result?: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// Streaming Callbacks
// -----------------------------------------------------------------------------

/**
 * Callbacks for handling SSE events during chat streaming.
 */
export interface ChatStreamCallbacks {
  /** Called when status event received (e.g., 'thinking', 'processing') */
  onStatus?: (status: string, detail?: string) => void;
  /** Called when text delta received (incremental text) */
  onDelta?: (delta: string, messageId: string) => void;
  /** Called when content blocks appended */
  onBlocksAppend?: (blocks: ChatContentBlock[], messageId: string) => void;
  /** Called when message is complete */
  onComplete?: (messageId: string) => void;
  /** Called on error */
  onError?: (errorCode: string, detail: string) => void;
  /** Called when stream is done */
  onDone?: () => void;
  /** Called when tool operation starts */
  onToolStarted?: (toolName: string, data: Record<string, unknown>) => void;
  /** Called when tool proposes an action */
  onToolProposed?: (proposalId: string, data: Record<string, unknown>) => void;
  /** Called when tool operation completes */
  onToolResult?: (data: Record<string, unknown>) => void;
}
