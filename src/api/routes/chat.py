"""Chat streaming endpoint."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from src.api.models import ChatRequest
from src.agent.streaming_agent import create_streaming_response
from src.logging_config import get_logger

logger = get_logger("chatbot.routes.chat")

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat responses with real-time tool execution updates.

    Args:
        request: ChatRequest containing message, conversation history, and optional session_id

    Returns:
        StreamingResponse with Server-Sent Events (SSE)
    """
    logger.info(f"Chat request received: {request.message[:50]}...")

    return StreamingResponse(
        create_streaming_response(
            message=request.message,
            conversation_history=request.conversation_history,
            session_id=request.session_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
