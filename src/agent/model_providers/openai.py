"""OpenAI model provider implementation."""
from strands.models.openai import OpenAIModel
from .base import BaseModelProvider
from ...config import Config
from ...utils.token_tracker import get_request_tracker
from ...logging_config import get_logger

logger = get_logger("chatbot.openai_provider")


class OpenAIProvider(BaseModelProvider):
    """Provider for OpenAI models."""

    def __init__(self, model_id: str = "gpt-5-mini"):
        """
        Initialize OpenAI provider.

        Args:
            model_id: OpenAI model ID to use (default: gpt-5-mini)
        """
        self.api_key = Config.OPENAI_API_KEY
        self.model_id = Config.OPENAI_MODEL_ID
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.temperature = Config.LLM_TEMPERATURE

    def get_model(self) -> OpenAIModel:
        """
        Get OpenAI model instance with token tracking.

        Returns:
            Initialized OpenAIModel
        """
        model = OpenAIModel(
            client_args={"api_key": self.api_key},
            model_id=self.model_id,
            params={
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream_options": {"include_usage": True},  # Include usage in streaming response
            }
        )

        # Monkey-patch the model's stream method to track usage
        original_stream = model.stream

        async def tracked_stream(*args, **kwargs):
            # Stream through the original method
            tracker = get_request_tracker()
            cumulative_input = 0
            cumulative_output = 0
            chunk_count = 0
            all_chunks = []  # Store all chunks to check last ones

            async for chunk in original_stream(*args, **kwargs):
                chunk_count += 1
                all_chunks.append(chunk)

                # Try to extract usage from streaming chunks (chunks are dicts)
                # Strands wraps usage in metadata object
                if isinstance(chunk, dict):
                    usage = None

                    # Check for metadata.usage (Strands format)
                    if 'metadata' in chunk and 'usage' in chunk['metadata']:
                        usage = chunk['metadata']['usage']
                    # Also check for direct usage key (OpenAI format)
                    elif 'usage' in chunk:
                        usage = chunk['usage']

                    if usage:
                        logger.debug(f"[OPENAI] Found usage in chunk {chunk_count}: {usage}")

                        # Handle both camelCase (Strands) and snake_case (OpenAI)
                        input_tokens = usage.get('inputTokens', 0) or usage.get('prompt_tokens', 0) or usage.get('input_tokens', 0)
                        output_tokens = usage.get('outputTokens', 0) or usage.get('completion_tokens', 0) or usage.get('output_tokens', 0)

                        # Track total tokens
                        if input_tokens > 0 or output_tokens > 0:
                            cumulative_input = input_tokens
                            cumulative_output = output_tokens

                yield chunk

            # Log final usage and track it
            logger.info(f"[OPENAI] Processed {chunk_count} chunks")
            if cumulative_input > 0 or cumulative_output > 0:
                # Track the total usage
                usage_dict = {
                    'prompt_tokens': cumulative_input,
                    'completion_tokens': cumulative_output
                }
                tracker.add_completion_usage(usage_dict, self.model_id)
                logger.info(f"[OPENAI] Model: {self.model_id} | Input: {cumulative_input:,} tokens | Output: {cumulative_output:,} tokens")
            else:
                logger.warning(f"[OPENAI] No usage data captured from streaming response!")

        model.stream = tracked_stream

        return model

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "openai"

    def is_available(self) -> bool:
        """
        Check if OpenAI is available.

        Returns:
            True if OPENAI_API_KEY is configured
        """
        return bool(self.api_key)
