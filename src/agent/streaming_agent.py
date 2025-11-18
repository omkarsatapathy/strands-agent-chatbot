"""Streaming agent implementation for real-time tool execution updates.

This implementation follows Strands best practices:
- Uses async iterators (stream_async) for FastAPI
- No callback handler (async iterator provides all events)
- Processes events directly as they stream from the agent
"""
import json
import time
from typing import List, Dict, AsyncGenerator
from strands import Agent
from strands.models.llamacpp import LlamaCppModel
from strands_tools import calculator
from ..config import Config
from ..logging_config import get_logger
from ..tools.google_search import google_search_with_context
from ..tools.datetime_ist import get_current_datetime_ist
from .callback_handler import ToolLimitHook

logger = get_logger("chatbot.streaming")


async def create_streaming_response(
    message: str,
    conversation_history: List[Dict[str, str]]
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

    Yields:
        SSE-formatted strings with event updates
    """
    try:
        # Initialize model
        model = LlamaCppModel(
            base_url=Config.LLAMA_CPP_URL,
            model_id="default",
            params={
                "max_tokens": Config.LLM_MAX_TOKENS,
                "temperature": Config.LLM_TEMPERATURE,
                "repeat_penalty": 1.1,
            }
        )

        # Convert conversation history to Strands format
        history_messages = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_messages.append({
                "role": role,
                "content": [{"text": content}]
            })

        logger.info(f"Starting streaming agent with {len(history_messages)} history messages")
        logger.info(f"📩 User message: {message}")

        # Create hook for tool limit enforcement
        tool_limit_hook = ToolLimitHook(max_calls=Config.MAX_TOOL_CALLS)

        # Initialize agent WITHOUT callback handler (best practice for async iterators)
        agent = Agent(
            model=model,
            tools=[calculator, google_search_with_context, get_current_datetime_ist],
            system_prompt=Config.get_system_prompt(),
            messages=history_messages,
            hooks=[tool_limit_hook],
            # verbose = True,
            callback_handler=None  # No callback handler needed with stream_async
        )

        # Send connected event
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"

        # Send initial thinking event
        yield f"event: thinking\ndata: {json.dumps({'status': 'Thinking...'})}\n\n"

        # Map tool names to display names with emojis
        tool_display_names = {
            'calculator': '🧮 Calculating',
            'google_search_with_context': '🌐 Searching the web',
            'get_current_datetime_ist': '🕐 Getting current time'
        }

        # Track state
        tool_count = 0
        previous_tool_use = None
        complete_response = ""
        last_heartbeat = time.time()

        # Stream events using async iterator (Strands best practice)
        async for event in agent.stream_async(message):

            # Handle text generation (response chunks)
            if "data" in event:
                text_chunk = event["data"]
                complete_response += text_chunk
                # Note: We don't stream text chunks, only tool events
                # Text will be sent at the end

            # Handle tool usage events
            elif "current_tool_use" in event:
                tool_use = event["current_tool_use"]

                # Only emit unique tool uses (avoid duplicates)
                if previous_tool_use != tool_use and tool_use.get("name"):
                    previous_tool_use = tool_use
                    tool_count += 1

                    tool_name = tool_use.get('name', 'unknown')
                    display_name = tool_display_names.get(tool_name, f'🔧 {tool_name}')

                    tool_data = {
                        'status': display_name,
                        'tool_name': tool_name,
                        'display_name': display_name,
                        'tool_count': tool_count,
                        'max_tools': Config.MAX_TOOL_CALLS
                    }

                    yield f"event: tool\ndata: {json.dumps(tool_data)}\n\n"
                    logger.info(f"🔧 Tool #{tool_count}/{Config.MAX_TOOL_CALLS}: {display_name}")

            # Handle event loop lifecycle events
            elif event.get("init_event_loop", False):
                logger.info("🤖 Agent initialized...")
                yield f"event: thinking\ndata: {json.dumps({'status': 'Getting ready...'})}\n\n"

            elif event.get("start_event_loop", False):
                logger.info("⚙️  Agent is processing...")
                yield f"event: thinking\ndata: {json.dumps({'status': 'Processing...'})}\n\n"

            # Send periodic heartbeat to keep connection alive
            if time.time() - last_heartbeat > 15:
                yield ": heartbeat\n\n"
                last_heartbeat = time.time()

        # Send completion event with full response
        completion_data = {
            'status': 'Done!' if tool_count == 0 else f'Done! (used {tool_count} tool{"s" if tool_count > 1 else ""})',
            'response': complete_response,
            'tool_count': tool_count
        }
        yield f"event: done\ndata: {json.dumps(completion_data)}\n\n"
        logger.info(f"✅ Streaming completed. Tools used: {tool_count}")
        logger.info(f"📝 Response: {complete_response}")

    except Exception as e:
        logger.error(f"Streaming error: {str(e)}", exc_info=True)
        error_data = {
            'error': str(e),
            'type': type(e).__name__
        }
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
