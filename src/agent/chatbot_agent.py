"""Strands Agent for chatbot."""
from strands import Agent
from strands.models.llamacpp import LlamaCppModel
from strands_tools import calculator
from ..config import Config
from ..logging_config import get_logger
from ..tools.google_search import google_search_with_context
from ..tools.datetime_ist import get_current_datetime_ist

logger = get_logger("chatbot.agent")


async def create_chatbot_agent(paylaod) -> str:
    """
    Create and return a Strands agent response.

    Args:
        paylaod: Dictionary containing the prompt and conversation_history

    Returns:
        Agent response text
    """
    logger.info("Creating Strands chatbot agent")

    model = LlamaCppModel(
        base_url=Config.LLAMA_CPP_URL,
        model_id="default",
        params={
            "max_tokens": Config.LLM_MAX_TOKENS,
            "temperature": Config.LLM_TEMPERATURE,

            "repeat_penalty": 1.1,
        }
    )

    try:
        # Get conversation history from payload
        conversation_history = paylaod.get("conversation_history", [])

        # Build the full conversation context in Strands format
        # Convert history to the format expected by the agent: {"role": "user/assistant", "content": [{"text": "..."}]}
        history_messages = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_messages.append({
                "role": role,
                "content": [{"text": content}]
            })

        logger.info(f"Initializing agent with {len(history_messages)} history messages")

        # Initialize agent with conversation history
        agent = Agent(
            model=model,
            tools=[calculator, google_search_with_context, get_current_datetime_ist],
            system_prompt=Config.get_system_prompt(),
            messages=history_messages, 
            verbose=True
        )

        # Invoke agent with current prompt
        response = await agent.invoke_async(paylaod.get("prompt"))
        response_text = str(response)
        logger.info("Strands agent completed successfully")
        return response_text

    except Exception as e:
        logger.error(f"Agent failed: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"
