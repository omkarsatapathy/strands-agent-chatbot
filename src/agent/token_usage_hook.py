"""Hook to track token usage from model responses."""
from strands.hooks import BaseHook
from ..utils.token_tracker import get_request_tracker
from ..logging_config import get_logger

logger = get_logger("chatbot.token_hook")


class TokenUsageHook(BaseHook):
    """Hook to capture and track token usage from model responses."""

    def __init__(self, model_id: str = "gpt-4o-mini"):
        """
        Initialize the token usage hook.

        Args:
            model_id: Model ID for cost calculation
        """
        self.model_id = model_id
        self.tracker = get_request_tracker()

    async def on_completion_response(self, response):
        """
        Called when a completion response is received.

        Args:
            response: The response object from the model
        """
        try:
            # Try to extract usage from response
            if hasattr(response, 'usage') and response.usage:
                usage_dict = {
                    'prompt_tokens': getattr(response.usage, 'input_tokens', 0),
                    'completion_tokens': getattr(response.usage, 'output_tokens', 0)
                }
                self.tracker.add_completion_usage(usage_dict, self.model_id)
                logger.info(f"[TOKEN HOOK] Tracked: {usage_dict}")

        except Exception as e:
            logger.error(f"[TOKEN HOOK] Error tracking tokens: {e}")

        return response

    async def on_stream_chunk(self, chunk):
        """
        Called for each streaming chunk.

        Args:
            chunk: The streaming chunk
        """
        # Check if this chunk contains usage information
        try:
            if hasattr(chunk, 'usage') and chunk.usage:
                usage_dict = {
                    'prompt_tokens': getattr(chunk.usage, 'input_tokens', 0),
                    'completion_tokens': getattr(chunk.usage, 'output_tokens', 0)
                }
                if usage_dict['prompt_tokens'] > 0 or usage_dict['completion_tokens'] > 0:
                    self.tracker.add_completion_usage(usage_dict, self.model_id)
                    logger.info(f"[TOKEN HOOK] Tracked from stream: {usage_dict}")

        except Exception as e:
            logger.debug(f"[TOKEN HOOK] No usage in chunk: {e}")

        return chunk
