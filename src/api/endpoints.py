import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.core.database import get_firestore_db
from src.core.models import (
    ActionData,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ChatStreamRequest,
    Message,
)
from src.core.security import rate_limited_api_key, validate_api_key
from src.core.services import ChatbotService

logger = logging.getLogger(__name__)

v1_router = APIRouter()
v2_router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _service(request: Request) -> ChatbotService:
    return ChatbotService(get_firestore_db(request))


# ── v1 (deprecated) ───────────────────────────────────────────────────────────


@v1_router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(rate_limited_api_key)],
    deprecated=True,
)
async def chat_v1(request_data: ChatRequest, request: Request):
    """Synchronous chat endpoint. Deprecated — use POST /api/v2/chat/stream."""
    service = _service(request)
    try:
        chat_id = await service.get_or_create_session(request_data.chatId)
        result = await service.generate_response(chat_id, request_data.message)
        return ChatResponse(
            chatId=result["chatId"],
            message=result["message"],
            action=ActionData(**result["action"]),
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"v1 chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@v1_router.get(
    "/chat/{chat_id}/history",
    response_model=ChatHistoryResponse,
    dependencies=[Depends(validate_api_key)],
)
async def get_history_v1(chat_id: str, limit: int = 50, request: Request = None):
    service = _service(request)
    try:
        messages_data = await service.get_history(chat_id, limit)
        messages = [
            Message(role=msg["role"], content=msg["content"], timestamp=msg.get("timestamp"))
            for msg in messages_data
        ]
        return ChatHistoryResponse(chatId=chat_id, messages=messages, totalMessages=len(messages))
    except Exception as e:
        logger.error(f"History error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving chat history") from e


@v1_router.delete("/chat/{chat_id}", dependencies=[Depends(validate_api_key)])
async def delete_session_v1(chat_id: str, request: Request):
    service = _service(request)
    try:
        if await service.delete_session(chat_id):
            return {"message": "Session deleted successfully"}
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting session") from e


@v1_router.get("/health")
async def health_v1():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc), "version": "1.0.0"}


@v1_router.get("/stats", dependencies=[Depends(validate_api_key)])
async def stats_v1(request: Request):
    service = _service(request)
    try:
        return {
            "totalSessions": await service.count_sessions(),
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving statistics") from e


# ── v2 ────────────────────────────────────────────────────────────────────────


@v2_router.post("/chat/stream", dependencies=[Depends(rate_limited_api_key)])
async def stream_chat_v2(request_data: ChatStreamRequest, request: Request):
    """
    Streaming chat endpoint. Returns Server-Sent Events.
    Events: meta | thinking | handoff | tool_call | tool_result | citation | action | token | done
    """
    from src.core.agent_orchestrator import get_main_agent_workflow

    service = _service(request)
    chat_id = await service.get_or_create_session(request_data.chatId)
    history_data = await service.get_history(chat_id)
    llm_history = service.build_llm_history(history_data)

    await service.save_message(chat_id, "user", request_data.message)

    async def event_generator() -> AsyncGenerator[str, None]:
        yield _sse("meta", {"chatId": chat_id, "agent": "router_agent"})

        agent_workflow = get_main_agent_workflow()
        handler = agent_workflow.run(user_msg=request_data.message, chat_history=llm_history)

        response_parts: list[str] = []
        current_agent: str = "router_agent"

        try:
            async for event in handler.stream_events():
                # ── detect agent change (handoff) ──────────────────────────
                event_agent = getattr(event, "current_agent_name", None)
                if event_agent and event_agent != current_agent:
                    yield _sse("handoff", {"from": current_agent, "to": event_agent})
                    current_agent = event_agent

                # ── streaming token ────────────────────────────────────────
                delta = getattr(event, "delta", None)
                if isinstance(delta, str) and delta:
                    response_parts.append(delta)
                    yield _sse("token", {"text": delta})
                    continue

                # ── tool call (list of ToolSelection) ──────────────────────
                tool_calls = getattr(event, "tool_calls", None)
                if tool_calls and not delta:
                    for tc in tool_calls:
                        name = getattr(tc, "tool_name", str(tc))
                        kwargs = getattr(tc, "tool_kwargs", {})
                        yield _sse("thinking", {"agent": current_agent, "step": f"calling {name}"})
                        yield _sse("tool_call", {"tool": name, "input": kwargs})
                    continue

                # ── tool result ────────────────────────────────────────────
                tool_output = getattr(event, "tool_output", None)
                if tool_output is not None:
                    tool_call_obj = getattr(event, "tool_call", None)
                    tool_name = getattr(tool_call_obj, "tool_name", "unknown")

                    # Extract citations and actions embedded in the tool output
                    try:
                        raw = getattr(tool_output, "content", tool_output)
                        output_data = json.loads(raw) if isinstance(raw, str) else raw
                        if isinstance(output_data, dict):
                            for citation in output_data.get("_citations", []):
                                yield _sse("citation", citation)
                            action = output_data.get("_action")
                            if action:
                                yield _sse("action", action)
                    except Exception:
                        pass

                    yield _sse("tool_result", {"tool": tool_name, "result_summary": "done"})

        except Exception as e:
            logger.error(f"Streaming error for {chat_id}: {e}", exc_info=True)

        final_text = "".join(response_parts)
        if final_text:
            await service.save_message(chat_id, "assistant", final_text, agent=current_agent)

        yield _sse("done", {"chatId": chat_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@v2_router.get(
    "/chat/{chat_id}/history",
    response_model=ChatHistoryResponse,
    dependencies=[Depends(validate_api_key)],
)
async def get_history_v2(chat_id: str, limit: int = 50, request: Request = None):
    service = _service(request)
    try:
        messages_data = await service.get_history(chat_id, limit)
        messages = [
            Message(role=msg["role"], content=msg["content"], timestamp=msg.get("timestamp"))
            for msg in messages_data
        ]
        return ChatHistoryResponse(chatId=chat_id, messages=messages, totalMessages=len(messages))
    except Exception as e:
        logger.error(f"History v2 error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving chat history") from e


@v2_router.delete("/chat/{chat_id}", dependencies=[Depends(validate_api_key)])
async def delete_session_v2(chat_id: str, request: Request):
    service = _service(request)
    try:
        if await service.delete_session(chat_id):
            return {"message": "Session deleted successfully"}
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete v2 error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting session") from e


@v2_router.get("/health")
async def health_v2():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc), "version": "2.0.0"}


@v2_router.get("/stats", dependencies=[Depends(validate_api_key)])
async def stats_v2(request: Request):
    service = _service(request)
    try:
        return {
            "totalSessions": await service.count_sessions(),
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as e:
        logger.error(f"Stats v2 error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving statistics") from e
