"""Chat assistant streaming endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from core.ratelimit import check_rate_limit
from schemas.chat_content import TextBlock
from schemas.chat_streaming import ChatSseEvent, ChatStreamRequest
from services.chat_agent import get_chat_agent, normalize_agent_output


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/conversations/{conversation_id}/messages/stream",
    response_class=StreamingResponse,
    dependencies=[Depends(check_rate_limit)],
)
async def stream_chat_message(
    conversation_id: UUID,
    payload: ChatStreamRequest,
) -> StreamingResponse:
    """Stream assistant responses using the canonical SSE envelope."""
    message_id = uuid4()
    agent = get_chat_agent()

    async def event_stream() -> AsyncGenerator[str, None]:
        yield ChatSseEvent(
            event="status",
            conversation_id=conversation_id,
            message_id=message_id,
            data={"status": "thinking"},
        ).to_sse()
        try:
            result = await agent.run(payload.content)
            message = normalize_agent_output(
                getattr(result, "output", None) or getattr(result, "data", None)
            )
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
        except Exception as exc:  # pragma: no cover - safeguard for streaming
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
