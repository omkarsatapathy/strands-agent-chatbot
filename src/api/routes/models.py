"""Model provider endpoints."""
from fastapi import APIRouter
from src.agent.model_providers import ModelProviderFactory
from src.logging_config import get_logger

logger = get_logger("chatbot.routes.models")

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/providers")
async def get_providers():
    """
    Get list of available model providers.

    Returns:
        Dictionary with available providers and default provider
    """
    try:
        providers = ModelProviderFactory.get_available_providers()

        # Try to get default provider
        try:
            default_provider = ModelProviderFactory.get_default_provider()
        except RuntimeError:
            default_provider = None

        return {
            "providers": providers,
            "default": default_provider
        }
    except Exception as e:
        logger.error(f"Error getting providers: {e}", exc_info=True)
        return {
            "providers": [],
            "default": None,
            "error": str(e)
        }
