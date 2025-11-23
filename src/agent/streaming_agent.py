"""Streaming agent implementation with Swarm pattern for multi-agent coordination.

This implementation follows Strands best practices:
- Uses async iterators (stream_async) for FastAPI
- No callback handler (async iterator provides all events)
- Processes events directly as they stream from the agent
- Implements Swarm pattern for autonomous agent collaboration
"""
import json
import re
import time
import warnings
from typing import List, Dict, AsyncGenerator, Optional

# Suppress OpenTelemetry context warnings that occur in async streaming
# This is a known issue with async context management across different coroutines
warnings.filterwarnings("ignore", message=".*was created in a different Context.*")

from strands import Agent
from strands.multiagent import Swarm
from strands_tools import calculator
from ..config import Config
from ..logging_config import get_logger
from ..tools.google_search import google_search_with_context
from ..tools.datetime_ist import get_current_datetime_ist
from ..tools.link_executor import fetch_url_content, fetch_multiple_urls
from ..tools.google_maps import (
    search_nearby_places,
    get_directions,
    get_traffic_info,
    get_place_details,
    explore_area
)
from .callback_handler import ToolLimitHook
from .model_providers import ModelProviderFactory
from .gmail_tool_wrappers import get_session_tools, get_gmail_tools
from ..utils.token_tracker import get_request_tracker, reset_request_tracker

logger = get_logger("chatbot.streaming")


async def create_streaming_response(
    message: str,
    conversation_history: List[Dict[str, str]],
    session_id: str = None,
    model_provider: Optional[str] = None,
    response_style: Optional[str] = None
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
        # Reset token tracker for this request
        reset_request_tracker()
        tracker = get_request_tracker()

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

        # Get model ID for cost calculation
        model_id = getattr(provider, 'model_id', 'gpt-4o-mini')

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

        # Build system prompt with response style modifier
        base_system_prompt = Config.get_system_prompt()
        style_name = response_style or Config.DEFAULT_RESPONSE_STYLE
        style_modifier = Config.RESPONSE_STYLES.get(style_name, "")

        if style_modifier:
            system_prompt = f"{base_system_prompt}\n\n[Response Style: {style_name}]\n{style_modifier}"
            logger.info(f"🎨 Using response style: {style_name}")
        else:
            system_prompt = base_system_prompt
            logger.info(f"🎨 Using default response style: Normal")

        # Create hook for tool limit enforcement
        tool_limit_hook = ToolLimitHook(max_calls=Config.MAX_TOOL_CALLS)

        # Build tools list for primary orchestrator agent
        primary_tools = [calculator, get_current_datetime_ist]

        # Add session-specific tools if session_id is provided
        if session_id:
            session_tools = get_session_tools(session_id)
            primary_tools.extend(session_tools)

        # Create News Reader Agent (specialized for email and news analysis)
        news_tools = get_gmail_tools()
        news_reader_agent = Agent(
            name="Gmail Reader Agent",
            model=model,
            tools=news_tools,
            system_prompt=Config.get_news_reader_agent_prompt(),
            hooks=[tool_limit_hook],
            callback_handler=None
        )

        # Create Researcher Agent (specialized for web research and information gathering)
        researcher_tools = [google_search_with_context, fetch_url_content, fetch_multiple_urls]
        researcher_agent = Agent(
            name="Researcher Agent",
            model=model,
            tools=researcher_tools,
            system_prompt=Config.get_researcher_agent_prompt(),
            hooks=[tool_limit_hook],
            callback_handler=None
        )

        # Create Maps Agent (specialized for location, navigation, and traffic queries)
        maps_tools = [search_nearby_places, get_directions, get_traffic_info, get_place_details, explore_area]
        maps_agent = Agent(
            name="Maps Agent",
            model=model,
            tools=maps_tools,
            system_prompt=Config.get_maps_agent_prompt(),
            hooks=[tool_limit_hook],
            callback_handler=None
        )

        # Create Primary Orchestrator Agent
        orchestrator_agent = Agent(
            name="Orchestrator Agent",
            model=model,
            tools=primary_tools,
            system_prompt=system_prompt,
            messages=history_messages,
            hooks=[tool_limit_hook],
            callback_handler=None
        )

        # Create Swarm with all agents
        swarm = Swarm(
            nodes=[orchestrator_agent, news_reader_agent, researcher_agent, maps_agent],
            entry_point=orchestrator_agent,
            max_handoffs=4,
            max_iterations=6
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
            'fetch_url_content': '🔗 Fetching URL content',
            'fetch_multiple_urls': '🔗 Fetching multiple URLs',
            'search_nearby_places': '📍 Searching nearby places',
            'get_directions': '🗺️ Getting directions',
            'get_traffic_info': '🚗 Checking traffic',
            'get_place_details': '🏪 Getting place details',
            'explore_area': '🔍 Exploring area'
        }

        # Track handoff target agent dynamically
        current_handoff_target = None

        # Track state
        tool_count = 0
        previous_tool_use = None
        complete_response = ""
        last_heartbeat = time.time()
        maps_widget_data = None  # Store maps widget metadata from tool results

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
                    # Filter out handoff tool JSON output from response
                    # These are internal swarm messages, not user-facing content
                    if text_chunk.strip().startswith('{"status":"handoff'):
                        logger.debug(f"Filtering handoff JSON from response: {text_chunk[:50]}...")
                        continue
                    complete_response += text_chunk

                # Capture tool results to extract maps widget metadata
                elif "message" in inner_event:
                    msg = inner_event.get("message", {})
                    logger.info(f"🔍 Message event received. Type: {type(msg)}, Keys: {msg.keys() if isinstance(msg, dict) else 'N/A'}")
                    
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        # Tool results come as user messages with toolResult content
                        content_list = msg.get("content", [])
                        logger.info(f"🔍 Content list type: {type(content_list)}, Length: {len(content_list) if isinstance(content_list, list) else 'N/A'}")
                        
                        for idx, content_item in enumerate(content_list):
                            logger.info(f"🔍 Content item {idx}: Type={type(content_item)}, Keys={content_item.keys() if isinstance(content_item, dict) else 'N/A'}")
                            
                            if isinstance(content_item, dict) and "toolResult" in content_item:
                                tool_result = content_item["toolResult"]
                                logger.info(f"🔍 Tool result found! Type: {type(tool_result)}, Keys: {tool_result.keys() if isinstance(tool_result, dict) else 'N/A'}")
                                logger.info(f"🔍 Tool result content preview: {str(tool_result)[:500]}...")
                                
                                tr_content = tool_result.get("content", [])
                                
                                # Helper to extract widget from text
                                def extract_widget(text_content):
                                    if "<!--MAPS_WIDGET:" in text_content:
                                        match = re.search(r'<!--MAPS_WIDGET:(.*?)-->', text_content, re.DOTALL)
                                        if match:
                                            try:
                                                return json.loads(match.group(1))
                                            except json.JSONDecodeError:
                                                pass
                                    return None

                                # Handle content being a string
                                if isinstance(tr_content, str):
                                    logger.info(f"🔍 Tool result content is string, length: {len(tr_content)}")
                                    logger.info(f"🔍 Content preview: {tr_content[:200]}...")
                                    data = extract_widget(tr_content)
                                    if data:
                                        maps_widget_data = data
                                        logger.info(f"📍 Captured maps widget data with {len(maps_widget_data.get('maps_widget', {}).get('places', []))} places")
                                
                                # Handle content being a list of dicts
                                elif isinstance(tr_content, list):
                                    logger.info(f"🔍 Tool result content is list, length: {len(tr_content)}")
                                    for tc_idx, tc in enumerate(tr_content):
                                        logger.info(f"🔍 Content item {tc_idx}: Type={type(tc)}, Keys={tc.keys() if isinstance(tc, dict) else 'N/A'}")
                                        if isinstance(tc, dict) and "text" in tc:
                                            text_content = tc["text"]
                                            logger.info(f"🔍 Text content length: {len(text_content)}, preview: {text_content[:200]}...")
                                            data = extract_widget(text_content)
                                            if data:
                                                maps_widget_data = data
                                                logger.info(f"📍 Captured maps widget data with {len(maps_widget_data.get('maps_widget', {}).get('places', []))} places")

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

            # Get final result and track token usage
            elif event_type == "multiagent_result":
                result = event.get("result")
                if result:
                    status = getattr(result, 'status', 'completed')
                    logger.info(f"✅ Swarm completed: {status}")

                    # Try to extract token usage from result
                    # Strands may provide usage in result metadata
                    if hasattr(result, 'usage') and result.usage:
                        tracker.add_completion_usage(result.usage, model_id)
                        logger.info(f"📊 Tokens tracked: {result.usage}")

            # Send periodic heartbeat to keep connection alive
            if time.time() - last_heartbeat > 15:
                yield ": heartbeat\n\n"
                last_heartbeat = time.time()

        # Calculate cost for this request
        cost_data = tracker.calculate_cost(model_id=model_id)
        logger.info("=" * 80)
        logger.info(f"📊 TOKEN USAGE SUMMARY")
        logger.info(f"Model: {model_id}")
        logger.info(f"Input Tokens:  {cost_data['input_tokens']:,}")
        logger.info(f"Output Tokens: {cost_data['output_tokens']:,}")
        logger.info(f"Total Tokens:  {cost_data['total_tokens']:,}")
        logger.info(f"💰 Cost: ₹{cost_data['total_cost_inr']:.4f} (${cost_data['total_cost_usd']:.6f})")
        logger.info("=" * 80)

        # Append maps widget metadata to response if captured
        final_response = complete_response
        if maps_widget_data:
            logger.info(f"📍 Appending maps widget metadata to response")
            final_response += f"\n\n<!--MAPS_WIDGET:{json.dumps(maps_widget_data)}-->"

        # Send completion event with full response and cost
        completion_data = {
            'status': 'Done!' if tool_count == 0 else f'Done! (used {tool_count} tool{"s" if tool_count > 1 else ""})',
            'response': final_response,
            'tool_count': tool_count,
            'cost_inr': cost_data['total_cost_inr'],
            'cost_usd': cost_data['total_cost_usd'],
            'tokens': {
                'input': cost_data['input_tokens'],
                'output': cost_data['output_tokens'],
                'total': cost_data['total_tokens']
            }
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
