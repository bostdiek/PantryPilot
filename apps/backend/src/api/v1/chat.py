"""Chat assistant streaming endpoints."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic_ai import AgentRunResultEvent
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.ratelimit import check_rate_limit
from dependencies.auth import get_current_user
from dependencies.db import get_db
from models.chat_conversations import ChatConversation
from models.chat_pending_actions import ChatPendingAction
from models.chat_tool_calls import ChatToolCall
from models.users import User
from schemas.chat_content import TextBlock
from schemas.chat_streaming import ChatSseEvent, ChatStreamRequest
from schemas.chat_tools import ToolCancelRequest, ToolCancelResponse, ToolResultEnvelope
from services.chat_agent import get_chat_agent, normalize_agent_output


router = APIRouter(prefix="/chat", tags=["chat"])

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ToolCallStart:
    tool_name: str
    arguments: dict[str, object]
    started_at: datetime


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


async def _get_or_create_conversation(
    db: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID,
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

    conversation = ChatConversation(id=conversation_id, user_id=user_id)
    db.add(conversation)
    await db.commit()
    return conversation


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


async def _handle_agent_stream_event(
    event: object,
    *,
    conversation_id: UUID,
    message_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    tool_calls_by_id: dict[str, _ToolCallStart],
) -> tuple[str | None, object | None]:
    if isinstance(event, FunctionToolCallEvent):
        tool_name = _extract_tool_name(event.part)
        arguments = _extract_tool_arguments(event.part)
        tool_calls_by_id[event.tool_call_id] = _ToolCallStart(
            tool_name=tool_name,
            arguments=arguments,
            started_at=datetime.now(UTC),
        )
        return (
            ChatSseEvent(
                event="tool.started",
                conversation_id=conversation_id,
                message_id=message_id,
                data={
                    "tool_call_id": event.tool_call_id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
            ).to_sse(),
            None,
        )

    if isinstance(event, FunctionToolResultEvent):
        tool_start = tool_calls_by_id.get(event.tool_call_id)
        tool_name = tool_start.tool_name if tool_start else "unknown"
        arguments = tool_start.arguments if tool_start else {}
        started_at = tool_start.started_at if tool_start else datetime.now(UTC)
        finished_at = datetime.now(UTC)

        result_content = getattr(event.result, "content", None)
        if isinstance(result_content, dict):
            persisted_result: dict[str, object] | None = result_content
        elif result_content is None:
            persisted_result = None
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

        return (
            ChatSseEvent(
                event="tool.result",
                conversation_id=conversation_id,
                message_id=message_id,
                data={
                    "tool_call_id": event.tool_call_id,
                    "tool_name": tool_name,
                    "status": "success",
                    "result": persisted_result,
                },
            ).to_sse(),
            None,
        )

    if isinstance(event, AgentRunResultEvent):
        result = event.result
        if hasattr(result, "output"):
            return None, result.output
        if hasattr(result, "data"):
            return None, result.data
        return None, result

    return None, None


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
async def stream_chat_message(
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
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        yield ChatSseEvent(
            event="status",
            conversation_id=conversation_id,
            message_id=message_id,
            data={"status": "thinking"},
        ).to_sse()
        try:
            tool_calls_by_id: dict[str, _ToolCallStart] = {}
            raw_output: object | None = None

            async for agent_event in agent.run_stream_events(payload.content):
                sse_line, result = await _handle_agent_stream_event(
                    agent_event,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    user_id=current_user.id,
                    db=db,
                    tool_calls_by_id=tool_calls_by_id,
                )
                if sse_line is not None:
                    yield sse_line
                if result is not None:
                    raw_output = result

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
                        data={"block": block.model_dump()},
                    ).to_sse()
            yield ChatSseEvent(
                event="message.complete",
                conversation_id=conversation_id,
                message_id=message_id,
                data={},
            ).to_sse()
        except Exception as exc:
            yield ChatSseEvent(
                event="error",
                conversation_id=conversation_id,
                message_id=message_id,
                data={"message": str(exc)},
            ).to_sse()
        finally:
            yield ChatSseEvent(
                event="done",
                conversation_id=conversation_id,
                message_id=message_id,
                data={},
            ).to_sse()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
