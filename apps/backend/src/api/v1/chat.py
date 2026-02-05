"""Chat assistant streaming endpoints."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import AgentRunResultEvent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import get_settings
from core.observability import get_tracer
from core.ratelimit import check_rate_limit
from crud.user_preferences import UserPreferencesCRUD
from dependencies.auth import get_current_user
from dependencies.db import get_db
from models.chat_conversations import ChatConversation
from models.chat_messages import ChatMessage
from models.chat_pending_actions import ChatPendingAction
from models.chat_tool_calls import ChatToolCall
from models.users import User
from schemas.chat_content import TextBlock
from schemas.chat_streaming import (
    ChatSseEvent,
    ChatStreamRequest,
    ConversationListResponse,
    ConversationSummary,
    MessageHistoryResponse,
    MessageSummary,
)
from schemas.chat_tools import ToolCancelRequest, ToolCancelResponse, ToolResultEnvelope
from services.chat_agent import (
    CHAT_SYSTEM_PROMPT,
    ChatAgentDeps,
    get_chat_agent,
    normalize_agent_output,
)
from services.chat_agent.training_capture import capture_training_sample
from services.memory_update import MemoryUpdateService


# -----------------------------------------------------------------------------
# Training Data Capture Helpers
# -----------------------------------------------------------------------------


@dataclass
class TrainingDataContext:
    """Context needed for building training data from an agent run."""

    agent_result: object
    tool_calls_by_id: dict[str, _ToolCallStart]
    raw_output: object


def _process_model_request_for_training(
    msg: ModelRequest,
    seen_user_msgs: set[str],
) -> list[dict[str, Any]]:
    """Process ModelRequest parts into training message format."""
    messages: list[dict[str, Any]] = []
    for part in msg.parts:
        if isinstance(part, SystemPromptPart):
            # Skip - we add CHAT_SYSTEM_PROMPT manually
            continue
        elif isinstance(part, UserPromptPart):
            # Deduplicate user messages (history + current)
            content_str = (
                part.content if isinstance(part.content, str) else str(part.content)
            )
            if content_str not in seen_user_msgs:
                seen_user_msgs.add(content_str)
                messages.append({"role": "user", "content": content_str})
        elif isinstance(part, ToolReturnPart):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": part.tool_call_id,
                    "content": part.model_response_str(),
                }
            )
    return messages


def _process_model_response_for_training(msg: ModelResponse) -> dict[str, Any] | None:
    """Process ModelResponse into a single training assistant message."""
    text_parts: list[str] = []
    tool_calls_list: list[dict[str, Any]] = []

    for resp_part in msg.parts:
        if isinstance(resp_part, TextPart) and resp_part.content:
            text_parts.append(resp_part.content)
        elif isinstance(resp_part, ToolCallPart):
            tool_calls_list.append(
                {
                    "id": resp_part.tool_call_id,
                    "type": "function",
                    "function": {
                        "name": resp_part.tool_name,
                        "arguments": json.dumps(resp_part.args_as_dict()),
                    },
                }
            )

    if not text_parts and not tool_calls_list:
        return None

    assistant_msg: dict[str, Any] = {"role": "assistant"}
    if text_parts:
        assistant_msg["content"] = " ".join(text_parts)
    if tool_calls_list:
        assistant_msg["tool_calls"] = tool_calls_list
    return assistant_msg


def _build_training_prompt_data(
    agent_result: object,
) -> list[dict[str, Any]]:
    """Build ChatML-format prompt data from agent result.

    Extracts messages from PydanticAI's all_messages() and converts to
    training-ready format with system prompt prepended.

    Args:
        agent_result: The result from agent.run() with all_messages() method

    Returns:
        List of message dicts in ChatML format
    """
    # NOTE: PydanticAI's `instructions` param is NOT in all_messages()
    # so we manually prepend CHAT_SYSTEM_PROMPT for training data.
    history_data: list[dict[str, Any]] = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT}
    ]

    all_msgs = (
        agent_result.all_messages() if hasattr(agent_result, "all_messages") else []
    )

    # Track seen user messages to avoid duplicates from history
    seen_user_msgs: set[str] = set()

    for msg in all_msgs:
        if isinstance(msg, ModelRequest):
            request_msgs = _process_model_request_for_training(msg, seen_user_msgs)
            history_data.extend(request_msgs)
        elif isinstance(msg, ModelResponse):
            assistant_msg = _process_model_response_for_training(msg)
            if assistant_msg:
                history_data.append(assistant_msg)

    return history_data


def _serialize_raw_output_for_training(raw_output: object) -> str:
    """Safely serialize raw LLM output for training data.

    Handles various output types with fallback serialization on failure.

    Args:
        raw_output: The raw output from the agent

    Returns:
        JSON string representation of the output
    """
    try:
        if hasattr(raw_output, "model_dump"):
            return json.dumps(raw_output.model_dump())
        elif isinstance(raw_output, dict):
            return json.dumps(raw_output)
        else:
            return str(raw_output)
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to serialize raw output for training: %s", exc)
        # Fallback: convert to string representation
        return str(raw_output)


def _get_tokens_from_usage(usage: object) -> tuple[int | None, int | None]:
    """Extract prompt and completion tokens from a usage object or dict."""
    if isinstance(usage, dict):
        prompt = usage.get("prompt_tokens")
        if prompt is None:
            prompt = usage.get("input_tokens")

        completion = usage.get("completion_tokens")
        if completion is None:
            completion = usage.get("output_tokens")
    else:
        prompt = getattr(usage, "prompt_tokens", None)
        if prompt is None:
            prompt = getattr(usage, "input_tokens", None)

        completion = getattr(usage, "completion_tokens", None)
        if completion is None:
            completion = getattr(usage, "output_tokens", None)
    return (prompt, completion)


def _sum_usage_from_messages(agent_result: object) -> tuple[int, int]:
    """Sum token usage from all ModelResponse messages."""
    from pydantic_ai.messages import ModelResponse

    all_msgs = (
        agent_result.all_messages() if hasattr(agent_result, "all_messages") else []
    )
    total_input = 0
    total_output = 0
    for msg in all_msgs:
        if isinstance(msg, ModelResponse) and hasattr(msg, "usage") and msg.usage:
            input_t, output_t = _get_tokens_from_usage(msg.usage)
            if input_t is not None:
                total_input += input_t
            if output_t is not None:
                total_output += output_t
    return (total_input, total_output)


def _extract_usage_metrics(
    agent_result: object | None,
) -> tuple[int | None, int | None, int | None]:
    """Extract token usage metrics from agent result.

    For streaming runs (especially Azure OpenAI), tries multiple approaches:
    1. Check agent_result.usage directly
    2. Sum usage from all ModelResponse messages in all_messages()
    3. Return None if unavailable
    """
    if agent_result is None:
        return (None, None, None)

    # Try direct usage access first
    usage = getattr(agent_result, "usage", None)
    if usage is not None:
        prompt_tokens, completion_tokens = _get_tokens_from_usage(usage)
        if prompt_tokens is not None or completion_tokens is not None:
            return (prompt_tokens, completion_tokens, None)

    # Fallback: sum usage from all ModelResponse messages (streaming)
    try:
        total_input, total_output = _sum_usage_from_messages(agent_result)
        if total_input > 0 or total_output > 0:
            return (
                total_input if total_input > 0 else None,
                total_output if total_output > 0 else None,
                None,
            )
    except Exception as exc:
        logger.debug(f"Failed to extract usage from all_messages: {exc}")

    return (None, None, None)


def _extract_model_metadata(agent_result: object | None) -> tuple[str, str | None]:
    """Resolve model name/version for training samples."""
    if agent_result is not None:
        model_name = getattr(agent_result, "model_name", None)
        model_version = getattr(agent_result, "model_version", None)
        if model_name:
            return (str(model_name), str(model_version) if model_version else None)

    settings = get_settings()
    provider = settings.LLM_PROVIDER
    model_name = settings.CHAT_MODEL
    return (f"{provider}:{model_name}", None)


router = APIRouter(prefix="/chat", tags=["chat"])

logger = logging.getLogger(__name__)

# Initialize tracer for custom spans
_tracer = get_tracer(__name__)

# Maximum content length for SSE events before truncation
# Balances between useful preview and staying well under MAX_SSE_EVENT_BYTES
MAX_CONTENT_PREVIEW_CHARS: int = 500

# If the client's clock is wildly wrong, it can cause the agent to propose meals
# for the wrong week/year (e.g., "tomorrow" resolving to an old date).
# We treat large skews as invalid client context and fall back to server time.
MAX_CLIENT_SERVER_DATETIME_SKEW: timedelta = timedelta(hours=36)


def _resolve_current_datetime(
    client_datetime_str: str | None,
    *,
    server_now: datetime,
) -> datetime:
    """Resolve the datetime context to inject into the chat agent.

    The frontend sends an ISO timestamp for better timezone awareness, but the
    server must not trust it blindly because client clocks can be incorrect.
    When the client value is missing, invalid, or far from server time, we
    fall back to server_now.
    """
    if server_now.tzinfo is None:
        raise ValueError("server_now must be timezone-aware")

    if not client_datetime_str:
        return server_now

    try:
        parsed = datetime.fromisoformat(client_datetime_str.replace("Z", "+00:00"))
    except ValueError:
        return server_now

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    parsed_utc = parsed.astimezone(UTC)
    if abs(parsed_utc - server_now.astimezone(UTC)) > MAX_CLIENT_SERVER_DATETIME_SKEW:
        logger.warning(
            "Ignoring client current_datetime due to large skew: client=%s server=%s",
            parsed_utc.isoformat(),
            server_now.astimezone(UTC).isoformat(),
        )
        return server_now

    return parsed_utc


def _get_user_friendly_error_message(exc: Exception) -> str:
    """Convert technical exceptions to user-friendly error messages.

    Handles common AI API errors like rate limits and overloaded models
    with actionable guidance for users.
    """
    exc_str = str(exc).lower()

    # Gemini API overload / service unavailable
    if "503" in exc_str or "overloaded" in exc_str or "unavailable" in exc_str:
        return (
            "The AI service is currently experiencing high demand. "
            "Please wait a moment and try again."
        )

    # Rate limiting
    if "429" in exc_str or "rate limit" in exc_str or "quota" in exc_str:
        return (
            "You've sent too many requests. Please wait a minute before trying again."
        )

    # Timeout errors
    if "timeout" in exc_str or "timed out" in exc_str:
        return (
            "The request took too long to complete. "
            "Please try a simpler question or try again later."
        )

    # Model behavior errors (validation failures, etc.)
    if "unexpectedmodelbehavior" in exc_str or "output validation" in exc_str:
        return (
            "The AI had trouble generating a response. "
            "Please try rephrasing your question."
        )

    # Network/connection errors
    if "connection" in exc_str or "network" in exc_str:
        return (
            "There was a network issue connecting to the AI service. "
            "Please check your connection and try again."
        )

    # Fall back to a generic message for unknown errors
    logger.error(f"Unhandled chat error: {exc}")
    return "Something went wrong. Please try again."


async def _mark_message_as_failed(db: AsyncSession, message_id: UUID) -> None:
    """Mark a streaming message as failed during error cleanup.

    This prevents dangling placeholder messages when an error occurs mid-stream.
    Errors during cleanup are logged but not raised to avoid masking the original error.
    """
    try:
        # If an earlier DB operation failed, the session may be in an aborted
        # transaction state. Roll back so cleanup queries can run.
        await db.rollback()
        db_result = await db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        orphaned_message = db_result.scalar_one_or_none()
        if orphaned_message and orphaned_message.message_metadata.get("streaming"):
            orphaned_message.message_metadata = {"streaming": False, "error": True}
            await db.commit()
    except Exception:
        logger.exception("Failed to mark message as failed during error cleanup")


# -----------------------------------------------------------------------------
# Conversation History Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List user conversations",
    description="Returns a paginated list of conversations for the authenticated user.",
)
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
    offset: int = 0,
) -> ConversationListResponse:
    """List all conversations for the current user with pagination."""
    # Validate and clamp pagination parameters
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    # Count total conversations for the user
    count_query = select(func.count(ChatConversation.id)).where(
        ChatConversation.user_id == current_user.id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch conversations with pagination, ordered by most recent activity
    query = (
        select(ChatConversation)
        .where(ChatConversation.user_id == current_user.id)
        .order_by(ChatConversation.last_activity_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    conversations = result.scalars().all()

    summaries = [
        ConversationSummary(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            last_activity_at=conv.last_activity_at.isoformat(),
        )
        for conv in conversations
    ]

    return ConversationListResponse(
        conversations=summaries,
        total=total,
        has_more=(offset + len(conversations)) < total,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description=(
        "Delete a conversation and all its messages. "
        "Requires the conversation to belong to the authenticated user."
    ),
)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a conversation and all its messages via cascade delete."""
    # Verify conversation exists and belongs to user
    query = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id,
    )
    result = await db.execute(query)
    conversation = result.scalars().one_or_none()

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Delete the conversation (messages will cascade delete automatically)
    await db.delete(conversation)
    await db.commit()


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageHistoryResponse,
    summary="Get message history",
    description="Returns paginated message history for a conversation.",
)
async def get_message_history(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    before_id: UUID | None = None,
) -> MessageHistoryResponse:
    """Fetch message history for a conversation with optional cursor pagination."""
    # Validate and clamp limit parameter
    limit = max(1, min(limit, 100))

    # Verify conversation exists and belongs to user
    conv_query = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id,
    )
    conv_result = await db.execute(conv_query)
    conversation = conv_result.scalars().one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Build message query with cursor-based pagination
    query = select(ChatMessage).where(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.user_id == current_user.id,
    )

    # If before_id is provided, validate it belongs to this conversation and user
    if before_id is not None:
        cursor_query = select(ChatMessage.created_at).where(
            ChatMessage.id == before_id,
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.user_id == current_user.id,
        )
        cursor_result = await db.execute(cursor_query)
        cursor_time = cursor_result.scalar()
        if cursor_time is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid before_id: message not found in this conversation",
            )
        query = query.where(ChatMessage.created_at < cursor_time)

    # Order by created_at ascending (oldest first) for chronological display
    query = query.order_by(ChatMessage.created_at.asc()).limit(limit + 1)

    result = await db.execute(query)
    messages = list(result.scalars().all())

    # Determine if there are more messages
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    summaries = [
        MessageSummary(
            id=msg.id,
            role=msg.role,
            content_blocks=msg.content_blocks,
            created_at=msg.created_at.isoformat(),
        )
        for msg in messages
    ]

    return MessageHistoryResponse(
        messages=summaries,
        has_more=has_more,
    )


# -----------------------------------------------------------------------------
# Helper Dataclasses and Functions
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class _ToolCallStart:
    tool_name: str
    arguments: dict[str, object]
    started_at: datetime
    call_order: int = 0


# Maximum messages to include in history for multi-turn context
MAX_HISTORY_MESSAGES = 50


def _extract_text_from_blocks(content_blocks: list[dict[str, Any]]) -> str:
    """Extract text content from content_blocks JSONB field."""
    texts: list[str] = []
    for block in content_blocks:
        if block.get("type") == "text":
            text = block.get("text", "")
            if text:
                texts.append(text)
    return "\n".join(texts)


def _convert_db_messages_to_pydantic_ai(
    messages: list[ChatMessage],
) -> list[ModelMessage]:
    """Convert database ChatMessage records to PydanticAI ModelMessage format.

    Args:
        messages: List of ChatMessage records from the database.

    Returns:
        List of ModelMessage for PydanticAI message_history.
    """
    result: list[ModelMessage] = []

    for msg in messages:
        if msg.role == "user":
            text_content = _extract_text_from_blocks(msg.content_blocks)
            if not text_content:
                continue
            result.append(
                ModelRequest(
                    parts=[
                        UserPromptPart(
                            content=text_content,
                            timestamp=msg.created_at,
                        )
                    ],
                )
            )
        elif msg.role == "assistant":
            parts: list[TextPart | ToolCallPart] = []
            text_content = _extract_text_from_blocks(msg.content_blocks)
            if text_content:
                parts.append(TextPart(content=text_content))

            tool_calls: list[ChatToolCall] = sorted(
                getattr(msg, "tool_calls", []),
                key=lambda tool_call: tool_call.started_at,
            )
            for tool_call in tool_calls:
                tool_call_id = tool_call.call_metadata.get(
                    "tool_call_id",
                    str(tool_call.id),
                )
                parts.append(
                    ToolCallPart(
                        tool_name=tool_call.tool_name,
                        args=tool_call.arguments,
                        tool_call_id=tool_call_id,
                    )
                )

            if parts:
                result.append(
                    ModelResponse(
                        parts=parts,
                        model_name="historical",
                        timestamp=msg.created_at,
                    )
                )

            if tool_calls:
                return_parts = [
                    ToolReturnPart(
                        tool_name=tool_call.tool_name,
                        content=tool_call.result or {},
                        tool_call_id=tool_call.call_metadata.get(
                            "tool_call_id", str(tool_call.id)
                        ),
                        timestamp=tool_call.finished_at or tool_call.started_at,
                    )
                    for tool_call in tool_calls
                    if tool_call.status == "success"
                ]
                if return_parts:
                    result.append(ModelRequest(parts=return_parts))

    return result


async def _load_conversation_history(
    db: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID,
    limit: int = MAX_HISTORY_MESSAGES,
) -> list[ModelMessage]:
    """Load previous messages from a conversation for multi-turn context."""
    query = (
        select(ChatMessage)
        .options(selectinload(ChatMessage.tool_calls))
        .where(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.user_id == user_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    messages = list(result.scalars().all())
    return _convert_db_messages_to_pydantic_ai(messages)


async def _update_conversation_activity(
    db: AsyncSession,
    *,
    conversation_id: UUID,
) -> None:
    """Update conversation's last_activity_at timestamp."""
    result = await db.execute(
        select(ChatConversation).where(ChatConversation.id == conversation_id)
    )
    conversation = result.scalars().one_or_none()
    if conversation:
        conversation.last_activity_at = datetime.now(UTC)


async def _get_pending_action(
    db: AsyncSession,
    *,
    proposal_id: UUID,
    user_id: UUID,
) -> ChatPendingAction | None:
    result = await db.execute(
        select(ChatPendingAction).where(
            ChatPendingAction.id == proposal_id,
            ChatPendingAction.user_id == user_id,
        )
    )
    return result.scalars().one_or_none()


def _generate_conversation_title() -> str:
    """Generate a user-friendly conversation title from current timestamp."""
    now = datetime.now(UTC)
    return now.strftime("Chat started %b %d, %Y at %I:%M %p")


async def _get_or_create_conversation(
    db: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID,
    title: str | None = None,
) -> ChatConversation:
    result = await db.execute(
        select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user_id,
        )
    )
    conversation = result.scalars().one_or_none()
    if conversation is not None:
        return conversation

    conversation = ChatConversation(
        id=conversation_id,
        user_id=user_id,
        title=title or _generate_conversation_title(),
    )
    db.add(conversation)
    await db.commit()
    return conversation


async def _create_assistant_message(
    db: AsyncSession,
    *,
    message_id: UUID,
    conversation_id: UUID,
    user_id: UUID,
) -> ChatMessage:
    """Create a placeholder assistant message before streaming starts.

    This ensures the chat_messages record exists before any tool calls
    are persisted, satisfying the foreign key constraint on chat_tool_calls.
    The content_blocks will be updated with the final response when streaming
    completes.
    """
    message = ChatMessage(
        id=message_id,
        conversation_id=conversation_id,
        user_id=user_id,
        role="assistant",
        content_blocks=[],  # Will be populated when streaming completes
        metadata={"streaming": True},
    )
    db.add(message)
    await db.commit()
    return message


def _extract_tool_name(part: object) -> str:
    tool_name = getattr(part, "tool_name", None) or getattr(part, "name", None)
    if not tool_name:
        logger.warning(
            "Tool name extraction failed for tool part type=%s",
            type(part).__name__,
        )
        return "unknown"
    return str(tool_name)


def _extract_tool_arguments(part: object) -> dict[str, object]:
    arguments = getattr(part, "args", None) or getattr(part, "arguments", None)
    if isinstance(arguments, dict):
        return {str(key): value for key, value in arguments.items()}
    return {}


def _truncate_large_fields_for_sse(
    result: dict[str, object] | None,
) -> dict[str, object] | None:
    """Remove or truncate large fields from tool results for SSE events.

    Tool results are persisted to the database in full, but SSE events have
    a 16KB size limit. This function creates a safe copy for SSE transmission
    by removing large content fields that would exceed the limit.

    The agent already has access to the full content during execution - this
    truncation only affects what gets sent to the frontend for display.
    """
    if result is None:
        return None

    # Create a shallow copy to avoid modifying the original.
    # This is safe because we only replace top-level values, not mutate nested objects.
    sse_safe_result = dict(result)

    # Remove large content fields that are commonly returned by tools
    # The AI already has this content in context; it doesn't need it in the SSE stream
    if "content" in sse_safe_result:
        content = sse_safe_result["content"]
        if isinstance(content, str) and len(content) > MAX_CONTENT_PREVIEW_CHARS:
            # Replace with a truncated summary
            sse_safe_result["content"] = (
                content[:MAX_CONTENT_PREVIEW_CHARS] + "... (truncated for display)"
            )

    # Handle search_recipes results - only stream query info, not the full results
    # The AI already has the results; the frontend doesn't need them in the SSE stream
    if "recipes" in sse_safe_result:
        recipes = sse_safe_result["recipes"]
        total_results = sse_safe_result.get("total_results")
        if isinstance(total_results, int):
            total = total_results
        elif isinstance(recipes, list):
            total = len(recipes)
        else:
            total = 0
        sse_safe_result["recipes"] = f"({total} recipes found)"

    return sse_safe_result


async def _handle_agent_stream_event(
    event: object,
    *,
    conversation_id: UUID,
    message_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    tool_calls_by_id: dict[str, _ToolCallStart],
    tool_call_order: list[int],
) -> tuple[list[str], object | None, list[dict[str, Any]]]:
    """Handle a single agent stream event and return SSE events to emit.

    Returns:
        A tuple of (list of SSE event strings, optional final result, emitted blocks).
        The list may contain multiple events (e.g., tool.result + blocks.append).
        Emitted blocks are content blocks from tool results (e.g., recipe_card).
    """
    if isinstance(event, FunctionToolCallEvent):
        tool_name = _extract_tool_name(event.part)
        arguments = _extract_tool_arguments(event.part)
        current_order = tool_call_order[0]
        tool_call_order[0] += 1
        tool_calls_by_id[event.tool_call_id] = _ToolCallStart(
            tool_name=tool_name,
            arguments=arguments,
            started_at=datetime.now(UTC),
            call_order=current_order,
        )
        return (
            [
                ChatSseEvent(
                    event="tool.started",
                    conversation_id=conversation_id,
                    message_id=message_id,
                    data={
                        "tool_call_id": event.tool_call_id,
                        "tool_name": tool_name,
                        "arguments": arguments,
                    },
                ).to_sse()
            ],
            None,
            [],
        )

    if isinstance(event, FunctionToolResultEvent):
        tool_start = tool_calls_by_id.get(event.tool_call_id)
        tool_name = tool_start.tool_name if tool_start else "unknown"
        arguments = tool_start.arguments if tool_start else {}
        started_at = tool_start.started_at if tool_start else datetime.now(UTC)
        call_order = tool_start.call_order if tool_start else -1
        finished_at = datetime.now(UTC)
        duration_ms = (finished_at - started_at).total_seconds() * 1000

        # Create tracing span for tool call
        with _tracer.start_as_current_span(f"tool_call:{tool_name}") as span:
            span.set_attribute("tool_name", tool_name)
            span.set_attribute("tool_call_id", event.tool_call_id)
            span.set_attribute("call_order", call_order)
            span.set_attribute("duration_ms", duration_ms)
            span.set_attribute("conversation_id", str(conversation_id))
            span.set_attribute("message_id", str(message_id))
            span.set_attribute("status", "success")

        result_content = getattr(event.result, "content", None)
        if isinstance(result_content, dict):
            persisted_result: dict[str, object] | None = result_content
        elif result_content is None:
            persisted_result = None
        elif isinstance(result_content, BaseModel):
            # Handle Pydantic models (e.g., MealPlanHistoryResponse)
            # by converting to dict
            persisted_result = result_content.model_dump(mode="json")
        else:
            logger.warning(
                "Tool result content had unexpected type %s; coercing to string",
                type(result_content).__name__,
            )
            persisted_result = {"content": str(result_content)}

        db.add(
            ChatToolCall(
                conversation_id=conversation_id,
                message_id=message_id,
                user_id=user_id,
                tool_name=tool_name,
                arguments=arguments,
                result=persisted_result,
                status="success",
                error=None,
                started_at=started_at,
                finished_at=finished_at,
                call_metadata={
                    "tool_call_id": event.tool_call_id,
                    "source": "pydantic_ai",
                },
            )
        )
        await db.commit()

        # Build list of SSE events to emit
        sse_events: list[str] = []

        # Emit tool.result event with truncated content to avoid SSE payload size limits
        # The full result is already persisted to the database above
        sse_safe_result = _truncate_large_fields_for_sse(persisted_result)
        sse_events.append(
            ChatSseEvent(
                event="tool.result",
                conversation_id=conversation_id,
                message_id=message_id,
                data={
                    "tool_call_id": event.tool_call_id,
                    "tool_name": tool_name,
                    "status": "success",
                    "result": sse_safe_result,
                },
            ).to_sse()
        )

        # Extract and emit recipe_card blocks from tool results (e.g., suggest_recipe)
        emitted_blocks: list[dict[str, Any]] = []
        if isinstance(persisted_result, dict) and "recipe_card" in persisted_result:
            recipe_card = persisted_result["recipe_card"]
            if (
                isinstance(recipe_card, dict)
                and recipe_card.get("type") == "recipe_card"
            ):
                emitted_blocks.append(recipe_card)
                sse_events.append(
                    ChatSseEvent(
                        event="blocks.append",
                        conversation_id=conversation_id,
                        message_id=message_id,
                        data={"blocks": [recipe_card]},
                    ).to_sse()
                )

        return (sse_events, None, emitted_blocks)

    if isinstance(event, AgentRunResultEvent):
        result = event.result
        # Return the full result object so callers can access new_messages()
        return ([], result, [])

    return ([], None, [])


@router.post(
    "/actions/{proposal_id}/accept",
    response_model=ToolResultEnvelope,
    dependencies=[Depends(check_rate_limit)],
)
async def accept_chat_action(
    proposal_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolResultEnvelope:
    """Accept (and execute) a previously proposed DB-mutating action.

    This endpoint enforces explicit user confirmation by requiring the action
    to exist in `chat_pending_actions` and to be owned by the authenticated
    user.
    """

    action = await _get_pending_action(
        db,
        proposal_id=proposal_id,
        user_id=current_user.id,
    )
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    if action.status != "proposed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Action is not in proposed state (status={action.status})",
        )

    now = datetime.now(UTC)
    action.accepted_at = now

    # MVP: DB-mutating tool execution is intentionally not implemented yet.
    # We still record acceptance and persist an auditable tool call record.
    error_message = "Tool execution is not implemented yet."
    action.status = "failed"
    action.executed_at = now
    action.updated_at = now
    action.error = error_message

    tool_call = ChatToolCall(
        conversation_id=action.conversation_id,
        message_id=action.message_id,
        user_id=action.user_id,
        tool_name=action.tool_name,
        arguments=action.arguments,
        status="error",
        error=error_message,
        started_at=now,
        finished_at=now,
        call_metadata={"proposal_id": str(action.id)},
    )
    db.add(tool_call)
    await db.commit()

    return ToolResultEnvelope(
        proposal_id=action.id,
        tool_name=action.tool_name,
        status="error",
        error=error_message,
    )


@router.post(
    "/actions/{proposal_id}/cancel",
    response_model=ToolCancelResponse,
    dependencies=[Depends(check_rate_limit)],
)
async def cancel_chat_action(
    proposal_id: UUID,
    payload: ToolCancelRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolCancelResponse:
    """Cancel a proposed DB-mutating action.

    Cancellations are retained (status + optional reason) for transparency and
    future analytics.
    """

    action = await _get_pending_action(
        db,
        proposal_id=proposal_id,
        user_id=current_user.id,
    )
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    if action.status != "proposed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Action is not in proposed state (status={action.status})",
        )

    now = datetime.now(UTC)
    action.status = "canceled"
    action.cancel_reason = payload.reason
    action.canceled_at = now
    action.updated_at = now
    await db.commit()

    return ToolCancelResponse(
        proposal_id=action.id,
        status="canceled",
        cancel_reason=action.cancel_reason,
    )


@router.post(
    "/conversations/{conversation_id}/messages/stream",
    response_class=StreamingResponse,
    dependencies=[Depends(check_rate_limit)],
)
async def stream_chat_message(  # noqa: C901
    conversation_id: UUID,
    payload: ChatStreamRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Stream assistant responses using the canonical SSE envelope."""
    message_id = uuid4()
    agent = get_chat_agent()

    # Enforce scoping. If the conversation doesn't exist yet, create it so the
    # client can choose the UUID and begin streaming immediately.
    await _get_or_create_conversation(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        title=payload.title,
    )

    # Save the user's message to the conversation
    user_message = ChatMessage(
        conversation_id=conversation_id,
        user_id=current_user.id,
        role="user",
        content_blocks=[{"type": "text", "text": payload.content}],
        metadata={},
    )
    db.add(user_message)

    # Update conversation activity timestamp
    await _update_conversation_activity(db, conversation_id=conversation_id)
    await db.commit()

    # Create assistant message placeholder before streaming. This ensures the
    # chat_messages record exists before any tool calls are persisted, which
    # satisfies the foreign key constraint on chat_tool_calls.
    await _create_assistant_message(
        db,
        message_id=message_id,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    # Load conversation history for multi-turn context
    message_history = await _load_conversation_history(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    async def event_stream() -> AsyncGenerator[str, None]:  # noqa: C901
        yield ChatSseEvent(
            event="status",
            conversation_id=conversation_id,
            message_id=message_id,
            data={"status": "thinking"},
        ).to_sse()
        try:
            run_started_at = time.monotonic()
            tool_calls_by_id: dict[str, _ToolCallStart] = {}
            # Counter for tool call ordering (use list for mutability in nested scope)
            tool_call_order: list[int] = [0]
            # Track memory update calls to detect excessive updates
            memory_update_count: int = 0
            raw_output: object | None = None
            agent_result: object | None = None  # Avoid NameError if stream ends early
            # Track blocks emitted from tool results (e.g., recipe cards)
            tool_emitted_blocks: list[dict[str, Any]] = []

            # Extract timezone context from client
            client_ctx = payload.client_context or {}
            user_timezone = client_ctx.get("user_timezone", "UTC")
            client_datetime_str = client_ctx.get("current_datetime")

            # Validate client-provided timestamp with 36-hour max skew tolerance,
            # fall back to server time when invalid or too skewed
            current_dt = _resolve_current_datetime(
                client_datetime_str, server_now=datetime.now(UTC)
            )

            # Load user preferences for personalization
            user_prefs_crud = UserPreferencesCRUD()
            user_prefs = await user_prefs_crud.get_by_user_id(db, current_user.id)

            # Load memory document content
            memory_service = MemoryUpdateService(db)
            memory_doc = await memory_service.get_memory_document(current_user.id)
            memory_content = memory_doc.content if memory_doc else None

            deps = ChatAgentDeps(
                db=db,
                user=current_user,
                current_datetime=current_dt,
                user_timezone=user_timezone,
                user_preferences=user_prefs,
                memory_content=memory_content,
            )
            async for agent_event in agent.run_stream_events(
                payload.content, deps=deps, message_history=message_history
            ):
                sse_events, result, emitted_blocks = await _handle_agent_stream_event(
                    agent_event,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    user_id=current_user.id,
                    db=db,
                    tool_calls_by_id=tool_calls_by_id,
                    tool_call_order=tool_call_order,
                )

                # Track memory updates and warn if excessive
                if isinstance(agent_event, FunctionToolCallEvent):
                    tool_name = _extract_tool_name(agent_event.part)
                    if tool_name == "update_user_memory":
                        memory_update_count += 1
                        if memory_update_count > 2:
                            logger.warning(
                                f"Excessive memory updates detected "
                                f"(count={memory_update_count}) in conversation "
                                f"{conversation_id} - possible agent loop"
                            )

                for sse_line in sse_events:
                    yield sse_line
                if emitted_blocks:
                    tool_emitted_blocks.extend(emitted_blocks)
                if result is not None:
                    agent_result = result  # Full result object with new_messages()

            # Extract output for normalization
            if hasattr(agent_result, "output"):
                raw_output = agent_result.output
            elif hasattr(agent_result, "data"):
                raw_output = agent_result.data
            else:
                raw_output = agent_result

            message = normalize_agent_output(raw_output)
            for block in message.blocks:
                if isinstance(block, TextBlock):
                    yield ChatSseEvent(
                        event="message.delta",
                        conversation_id=conversation_id,
                        message_id=message_id,
                        data={"delta": block.text},
                    ).to_sse()
                else:
                    yield ChatSseEvent(
                        event="blocks.append",
                        conversation_id=conversation_id,
                        message_id=message_id,
                        data={"blocks": [block.model_dump()]},
                    ).to_sse()

            # Update the assistant message with the final response content
            # Include both LLM text blocks and tool-emitted blocks (e.g., recipe cards)
            db_result = await db.execute(
                select(ChatMessage).where(ChatMessage.id == message_id)
            )
            assistant_message = db_result.scalar_one()
            all_blocks = [block.model_dump() for block in message.blocks]
            all_blocks.extend(tool_emitted_blocks)
            assistant_message.content_blocks = all_blocks
            assistant_message.message_metadata = {"streaming": False}

            # Update conversation activity timestamp
            await _update_conversation_activity(db, conversation_id=conversation_id)
            await db.commit()

            # Capture training sample (non-blocking, failures logged but ignored)
            try:
                # Build tool calls data from completed tool calls
                tool_calls_data = None
                if tool_calls_by_id:
                    tool_calls_data = {
                        call_id: {
                            "tool_name": tc.tool_name,
                            "arguments": tc.arguments,
                        }
                        for call_id, tc in tool_calls_by_id.items()
                    }

                # Build training data using helper functions
                history_data = _build_training_prompt_data(agent_result)
                raw_output_for_training = _serialize_raw_output_for_training(raw_output)

                prompt_tokens, completion_tokens, _ = _extract_usage_metrics(
                    agent_result
                )
                model_name, model_version = _extract_model_metadata(agent_result)
                latency_ms = int((time.monotonic() - run_started_at) * 1000)

                await capture_training_sample(
                    db,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    user_id=current_user.id,
                    raw_prompt=json.dumps(history_data),
                    raw_response=raw_output_for_training,
                    tool_calls=tool_calls_data,
                    model_name=model_name,
                    model_version=model_version,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    user=current_user,  # Pass user for synthetic detection
                )
            except Exception as capture_exc:
                logger.warning("Failed to capture training sample: %s", capture_exc)

            yield ChatSseEvent(
                event="message.complete",
                conversation_id=conversation_id,
                message_id=message_id,
                data={},
            ).to_sse()
        except Exception as exc:
            try:
                # Ensure the session isn't stuck in a failed transaction before
                # attempting cleanup writes/reads.
                await db.rollback()
            except Exception:
                logger.exception("Failed to rollback session after streaming error")
            # Mark orphaned placeholder message as failed to prevent dangling records
            await _mark_message_as_failed(db, message_id)

            # Provide user-friendly error messages for common API issues
            error_message = _get_user_friendly_error_message(exc)
            yield ChatSseEvent(
                event="error",
                conversation_id=conversation_id,
                message_id=message_id,
                data={"message": error_message},
            ).to_sse()
        finally:
            yield ChatSseEvent(
                event="done",
                conversation_id=conversation_id,
                message_id=message_id,
                data={},
            ).to_sse()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
