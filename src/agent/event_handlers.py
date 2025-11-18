"""SSE Event handlers for streaming agent responses."""
import json
import time
from typing import AsyncGenerator, Dict
from ..config import Config
from ..logging_config import get_logger

logger = get_logger("chatbot.events")

# Map tool names to display names with emojis
TOOL_DISPLAY_NAMES = {
    'calculator': '🧮 Calculating',
    'google_search_with_context': '🌐 Searching the web',
    'get_current_datetime_ist': '🕐 Getting current time',
    'query_documents': '📄 Analyzing documents',
    'query_documents_wrapper': '📄 Analyzing documents'
}


async def send_sse_event(event_type: str, data: Dict) -> str:
    """Format and return an SSE event string.

    Args:
        event_type: Type of the event (connected, thinking, tool, done, error)
        data: Event data dictionary

    Returns:
        Formatted SSE event string
    """
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def process_stream_events(agent, message: str) -> AsyncGenerator[str, None]:
    """Process events from the agent stream and yield SSE formatted strings.

    Args:
        agent: The Strands agent instance
        message: User's message to process

    Yields:
        SSE-formatted event strings
    """
    # Send connected event
    yield await send_sse_event('connected', {'status': 'connected'})

    # Send initial thinking event
    yield await send_sse_event('thinking', {'status': 'Thinking...'})

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
                display_name = TOOL_DISPLAY_NAMES.get(tool_name, f'🔧 {tool_name}')

                tool_data = {
                    'status': display_name,
                    'tool_name': tool_name,
                    'display_name': display_name,
                    'tool_count': tool_count,
                    'max_tools': Config.MAX_TOOL_CALLS
                }

                yield await send_sse_event('tool', tool_data)
                logger.info(f"🔧 Tool #{tool_count}/{Config.MAX_TOOL_CALLS}: {display_name}")

        # Handle event loop lifecycle events
        elif event.get("init_event_loop", False):
            logger.info("🤖 Agent initialized...")
            yield await send_sse_event('thinking', {'status': 'Getting ready...'})

        elif event.get("start_event_loop", False):
            logger.info("⚙️  Agent is processing...")
            yield await send_sse_event('thinking', {'status': 'Processing...'})

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
    yield await send_sse_event('done', completion_data)
    logger.info(f"✅ Streaming completed. Tools used: {tool_count}")
    logger.info(f"📝 Response: {complete_response}")
