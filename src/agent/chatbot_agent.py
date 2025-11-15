"""Strands Agent for chatbot."""
from strands import Agent
from strands.models.llamacpp import LlamaCppModel
from strands_tools import calculator
from ..config import Config
from ..logging_config import get_logger

logger = get_logger("chatbot.agent")


def create_chatbot_agent():
    """
    Create and return a Strands agent with LlamaCpp backend.

    Returns:
        Agent: Configured Strands Agent instance
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

    agent = Agent(model=model, tools=[calculator])
    logger.info("Strands agent created successfully")

    return agent
