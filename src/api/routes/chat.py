"""Chat endpoint routes."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from src.agent.streaming_agent import create_streaming_response
from ..models import ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream agent responses with real-time tool execution updates."""
    limited_history = request.conversation_history[-10:] if len(request.conversation_history) > 10 else request.conversation_history

    return StreamingResponse(
        create_streaming_response(
            request.message,
            limited_history,
            session_id=request.session_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
