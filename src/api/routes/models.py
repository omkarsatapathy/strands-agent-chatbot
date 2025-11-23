"""Model provider endpoints."""
from fastapi import APIRouter
from src.agent.model_providers import ModelProviderFactory
from src.config import Config
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


@router.get("/styles")
async def get_response_styles():
    """
    Get available response styles.

    Returns:
        Dictionary with available styles and default style
    """
    try:
        styles = list(Config.RESPONSE_STYLES.keys())
        return {
            "styles": styles,
            "default": Config.DEFAULT_RESPONSE_STYLE,
            "descriptions": {
                "Normal": "Default balanced responses",
                "Formal": "Professional, business-appropriate tone",
                "Explanatory": "Detailed explanations with examples",
                "Concise": "Brief, to-the-point responses",
                "Learning": "Teaching style with simple explanations"
            }
        }
    except Exception as e:
        logger.error(f"Error getting styles: {e}", exc_info=True)
        return {
            "styles": ["Normal"],
            "default": "Normal",
            "error": str(e)
        }
