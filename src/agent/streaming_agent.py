"""Streaming agent implementation with Swarm pattern for multi-agent coordination.

This implementation follows Strands best practices:
- Uses async iterators (stream_async) for FastAPI
- No callback handler (async iterator provides all events)
- Processes events directly as they stream from the agent
- Implements Swarm pattern for autonomous agent collaboration
"""
import json
import time
from typing import List, Dict, AsyncGenerator, Optional
from strands import Agent
from strands.multiagent import Swarm
from strands_tools import calculator
from ..config import Config
from ..logging_config import get_logger
from ..tools.google_search import google_search_with_context
from ..tools.datetime_ist import get_current_datetime_ist
from .callback_handler import ToolLimitHook
from .model_providers import ModelProviderFactory
from .gmail_tool_wrappers import get_session_tools, get_gmail_tools

logger = get_logger("chatbot.streaming")


async def create_streaming_response(
    message: str,
    conversation_history: List[Dict[str, str]],
    session_id: str = None,
    model_provider: Optional[str] = None
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
        session_id: Optional session ID for document queries
        model_provider: Model provider to use ('llamacpp', 'gemini', 'openai')

    Yields:
        SSE-formatted strings with event updates
    """
    try:
        # Initialize model using factory
        if model_provider:
            logger.info(f"Using model provider: {model_provider}")
            try:
                provider = ModelProviderFactory.create_provider(model_provider)
                model = provider.get_model()
                logger.info(f"✅ Model provider '{model_provider}' initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize '{model_provider}': {e}")
                # Fall back to default provider
                logger.info("Falling back to default provider")
                default_provider_name = ModelProviderFactory.get_default_provider()
                provider = ModelProviderFactory.create_provider(default_provider_name)
                model = provider.get_model()
        else:
            # Use default provider
            default_provider_name = ModelProviderFactory.get_default_provider()
            logger.info(f"Using default model provider: {default_provider_name}")
            provider = ModelProviderFactory.create_provider(default_provider_name)
            model = provider.get_model()

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
        logger.info(f"Total message: \n\n{history_messages}")
        logger.info(f"📩 User message: {message}")

        # Create hook for tool limit enforcement
        tool_limit_hook = ToolLimitHook(max_calls=Config.MAX_TOOL_CALLS)

        # Build tools list for primary orchestrator agent
        primary_tools = [calculator, google_search_with_context, get_current_datetime_ist]

        # Add session-specific tools if session_id is provided
        if session_id:
            session_tools = get_session_tools(session_id)
            primary_tools.extend(session_tools)

        # Create News Reader Agent (specialized for email and news analysis)
        news_tools = get_gmail_tools()
        news_reader_agent = Agent(
            name="News Reader Agent",
            model=model,
            tools=news_tools,
            system_prompt=Config.get_news_reader_agent_prompt(),
            hooks=[tool_limit_hook],
            callback_handler=None
        )

        # Create Primary Orchestrator Agent
        orchestrator_agent = Agent(
            name="Orchestrator Agent",
            model=model,
            tools=primary_tools,
            system_prompt=Config.get_system_prompt(),
            messages=history_messages,
            hooks=[tool_limit_hook],
            callback_handler=None
        )

        # Create Swarm with both agents
        swarm = Swarm(
            nodes=[orchestrator_agent, news_reader_agent],
            entry_point=orchestrator_agent,
            max_handoffs=3,
            max_iterations=5
        )

        # Send connected event
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"

        # Send initial thinking event
        yield f"event: thinking\ndata: {json.dumps({'status': 'Thinking...'})}\n\n"

        # Map tool names to display names with emojis
        tool_display_names = {
            'calculator': '🧮 Calculating',
            'google_search_with_context': '🌐 Searching the web',
            'get_current_datetime_ist': '🕐 Getting current time',
            'query_documents': '📄 Analyzing documents',
            'query_documents_wrapper': '📄 Analyzing documents',
            'fetch_gmail_messages': '📧 Fetching news from emails',
            'fetch_gmail_wrapper': '📧 Fetching news from emails',
            'gmail_auth_status': '🔐 Checking Gmail auth status',
            'gmail_auth_wrapper': '🔐 Checking Gmail auth status',
            'handoff_to_agent': '🔄 Handing off to News Reader Agent'
        }

        # Track state
        tool_count = 0
        previous_tool_use = None
        complete_response = ""
        last_heartbeat = time.time()

        # Stream events using async iterator (Strands best practice with Swarm)
        async for event in swarm.stream_async(message):
            event_type = event.get("type")

            # Track multi-agent node execution
            if event_type == "multiagent_node_start":
                agent_name = event.get('node_id', 'Unknown')
                logger.info(f"🔄 Agent {agent_name} taking control")
                yield f"event: thinking\ndata: {json.dumps({'status': f'{agent_name} working...'})}\n\n"

            # Monitor agent events (nested events from individual agents)
            elif event_type == "multiagent_node_stream":
                inner_event = event.get("event", {})

                # Handle text generation from agents
                if "data" in inner_event:
                    text_chunk = inner_event["data"]
                    complete_response += text_chunk

                # Handle tool usage events from agents
                elif "current_tool_use" in inner_event:
                    tool_use = inner_event["current_tool_use"]

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

            # Track handoffs between agents
            elif event_type == "multiagent_handoff":
                from_agents = ", ".join(event.get('from_node_ids', []))
                to_agents = ", ".join(event.get('to_node_ids', []))
                logger.info(f"🔀 Handoff: {from_agents} → {to_agents}")
                yield f"event: thinking\ndata: {json.dumps({'status': f'Handing off to {to_agents}'})}\n\n"

            # Get final result
            elif event_type == "multiagent_result":
                result = event.get("result")
                if result:
                    status = getattr(result, 'status', 'completed')
                    logger.info(f"✅ Swarm completed: {status}")

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
