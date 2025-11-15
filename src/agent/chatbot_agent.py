"""Strands Agent for chatbot."""
from strands import Agent
from strands.models.llamacpp import LlamaCppModel
from strands_tools import calculator
from ..config import Config
from ..logging_config import get_logger
from ..tools.google_search import google_search_with_context

logger = get_logger("chatbot.agent")


async def create_chatbot_agent(paylaod) -> str:
    """
    Create and return a Strands agent response.

    Args:
        paylaod: Dictionary containing the prompt

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

    agent = Agent(
                model=model,
                tools=[calculator, google_search_with_context],
                system_prompt="You are an Inteligent Agent for chat bot You have 2 tools for math calculation and News update. Always identify yourself as Miccky and greet user with your name"
                )

    try:
        response = await agent.invoke_async(paylaod.get("prompt"))
        response_text = str(response)
        logger.info("Strands agent completed successfully")
        return response_text

    except Exception as e:
        logger.error(f"Agent failed: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"
