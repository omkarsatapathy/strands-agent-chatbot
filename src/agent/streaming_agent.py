"""Streaming agent implementation for real-time tool execution updates.

This implementation follows Strands best practices:
- Uses async iterators (stream_async) for FastAPI
- No callback handler (async iterator provides all events)
- Processes events directly as they stream from the agent
"""
import json
from typing import List, Dict, AsyncGenerator
from ..logging_config import get_logger
from .callback_handler import ToolLimitHook
from .agent_config import create_agent
from .event_handlers import process_stream_events
from ..config import Config

logger = get_logger("chatbot.streaming")


def convert_conversation_history(conversation_history: List[Dict[str, str]]) -> List[Dict]:
    """Convert conversation history to Strands message format.

    Args:
        conversation_history: List of messages with 'role' and 'content'

    Returns:
        List of messages in Strands format
    """
    history_messages = []
    for msg in conversation_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_messages.append({
            "role": role,
            "content": [{"text": content}]
        })
    return history_messages


async def create_streaming_response(
    message: str,
    conversation_history: List[Dict[str, str]],
    session_id: str = None
) -> AsyncGenerator[str, None]:
    """
    Create async generator for streaming agent responses with tool execution updates.

    Following Strands best practices:
    - Uses stream_async() for async framework (FastAPI)
    - Processes events directly from async iterator
    - No callback handler (not needed with async iterator)

    Args:
        message: User's message
        conversation_history: List of previous conversation messages
        session_id: Optional session ID for document-specific tools

    Yields:
        SSE-formatted strings with event updates
    """
    try:
        # Convert conversation history to Strands format
        history_messages = convert_conversation_history(conversation_history)

        logger.info(f"Starting streaming agent with {len(history_messages)} history messages")
        logger.info(f"Total message: \n\n{history_messages}")
        logger.info(f"📩 User message: {message}")

        # Create hook for tool limit enforcement
        tool_limit_hook = ToolLimitHook(max_calls=Config.MAX_TOOL_CALLS)

        # Create agent with all configurations
        agent = create_agent(
            session_id=session_id,
            history_messages=history_messages,
            hooks=[tool_limit_hook]
        )

        # Process and yield stream events
        async for sse_event in process_stream_events(agent, message):
            yield sse_event

    except Exception as e:
        logger.error(f"Streaming error: {str(e)}", exc_info=True)
        error_data = {
            'error': str(e),
            'type': type(e).__name__
        }
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
