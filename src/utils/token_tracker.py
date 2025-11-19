"""Token usage tracker for OpenAI API calls with cost calculation in INR."""
from typing import Dict, Optional
from threading import Lock
import functools


class TokenTracker:
    """Track token usage and calculate costs for OpenAI API calls."""

    # OpenAI pricing per 1M tokens (USD) - Updated Jan 2025
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }

    # TTS pricing per 1M characters (USD)
    TTS_PRICING = {
        "tts-1": 15.00,
        "tts-1-hd": 30.00,
    }

    # USD to INR conversion rate
    USD_TO_INR = 85.0

    def __init__(self):
        """Initialize token tracker."""
        self.input_tokens = 0
        self.output_tokens = 0
        self.tts_characters = 0
        self.lock = Lock()

    def add_completion_usage(self, usage_data: Dict, model_id: str = "gpt-4o-mini"):
        """
        Add token usage from a chat completion response.

        Args:
            usage_data: Usage dict from OpenAI response with prompt_tokens and completion_tokens
            model_id: Model ID used for the completion
        """
        with self.lock:
            self.input_tokens += usage_data.get("prompt_tokens", 0)
            self.output_tokens += usage_data.get("completion_tokens", 0)

    def add_tts_usage(self, text: str, model_id: str = "tts-1"):
        """
        Add TTS usage based on text length.

        Args:
            text: Text converted to speech
            model_id: TTS model ID used
        """
        with self.lock:
            self.tts_characters += len(text)

    def calculate_cost(self, model_id: str = "gpt-4o-mini", tts_model_id: str = "tts-1") -> Dict:
        """
        Calculate total cost in both USD and INR.

        Args:
            model_id: Model ID used for completions (default: gpt-4o-mini)
            tts_model_id: TTS model ID used (default: tts-1)

        Returns:
            Dict with token counts and costs
        """
        with self.lock:
            # Get pricing
            pricing = self.PRICING.get(model_id, {"input": 0, "output": 0})
            tts_pricing = self.TTS_PRICING.get(tts_model_id, 0)

            # Calculate completion costs (USD)
            input_cost_usd = (self.input_tokens / 1_000_000) * pricing["input"]
            output_cost_usd = (self.output_tokens / 1_000_000) * pricing["output"]

            # Calculate TTS costs (USD)
            tts_cost_usd = (self.tts_characters / 1_000_000) * tts_pricing

            # Total costs
            total_cost_usd = input_cost_usd + output_cost_usd + tts_cost_usd
            total_cost_inr = total_cost_usd * self.USD_TO_INR

            return {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.input_tokens + self.output_tokens,
                "tts_characters": self.tts_characters,
                "input_cost_usd": round(input_cost_usd, 6),
                "output_cost_usd": round(output_cost_usd, 6),
                "tts_cost_usd": round(tts_cost_usd, 6),
                "total_cost_usd": round(total_cost_usd, 6),
                "total_cost_inr": round(total_cost_inr, 4),
                "model_id": model_id,
                "tts_model_id": tts_model_id
            }

    def reset(self):
        """Reset all counters to zero."""
        with self.lock:
            self.input_tokens = 0
            self.output_tokens = 0
            self.tts_characters = 0

    def get_summary(self, model_id: str = "gpt-4o-mini", tts_model_id: str = "tts-1") -> str:
        """
        Get a human-readable summary of usage and costs.

        Args:
            model_id: Model ID used for completions
            tts_model_id: TTS model ID used

        Returns:
            Formatted string with usage summary
        """
        cost_data = self.calculate_cost(model_id, tts_model_id)

        summary = f"""
Token Usage Summary:
-------------------
Input Tokens:     {cost_data['input_tokens']:,}
Output Tokens:    {cost_data['output_tokens']:,}
Total Tokens:     {cost_data['total_tokens']:,}
TTS Characters:   {cost_data['tts_characters']:,}

Cost Breakdown:
--------------
Input Cost:       ${cost_data['input_cost_usd']:.6f} USD (₹{cost_data['input_cost_usd'] * self.USD_TO_INR:.4f})
Output Cost:      ${cost_data['output_cost_usd']:.6f} USD (₹{cost_data['output_cost_usd'] * self.USD_TO_INR:.4f})
TTS Cost:         ${cost_data['tts_cost_usd']:.6f} USD (₹{cost_data['tts_cost_usd'] * self.USD_TO_INR:.4f})

TOTAL COST:       ${cost_data['total_cost_usd']:.6f} USD (₹{cost_data['total_cost_inr']:.4f})
"""
        return summary


# Global singleton instance for request-level tracking
_request_tracker = None
_request_tracker_lock = Lock()


def get_request_tracker() -> TokenTracker:
    """Get or create the request-level token tracker instance."""
    global _request_tracker
    with _request_tracker_lock:
        if _request_tracker is None:
            _request_tracker = TokenTracker()
        return _request_tracker


def reset_request_tracker():
    """Reset the request-level token tracker."""
    global _request_tracker
    with _request_tracker_lock:
        if _request_tracker is not None:
            _request_tracker.reset()


def auto_track_usage(model_id: str = "gpt-4o-mini"):
    """
    Decorator to automatically track token usage from OpenAI API responses.

    Args:
        model_id: Model ID for cost calculation

    Returns:
        Decorated function that tracks usage
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Try to extract usage from result
            tracker = get_request_tracker()
            if hasattr(result, 'usage') and result.usage:
                usage_dict = {
                    'prompt_tokens': getattr(result.usage, 'prompt_tokens', 0) or getattr(result.usage, 'input_tokens', 0),
                    'completion_tokens': getattr(result.usage, 'completion_tokens', 0) or getattr(result.usage, 'output_tokens', 0)
                }
                tracker.add_completion_usage(usage_dict, model_id)

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Try to extract usage from result
            tracker = get_request_tracker()
            if hasattr(result, 'usage') and result.usage:
                usage_dict = {
                    'prompt_tokens': getattr(result.usage, 'prompt_tokens', 0) or getattr(result.usage, 'input_tokens', 0),
                    'completion_tokens': getattr(result.usage, 'completion_tokens', 0) or getattr(result.usage, 'output_tokens', 0)
                }
                tracker.add_completion_usage(usage_dict, model_id)

            return result

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
