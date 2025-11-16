"""Custom callback handler and hook for Strands agent to limit tool calls."""
from typing import Any
from strands.hooks import BeforeToolCallEvent, HookProvider
from ..logging_config import get_logger

logger = get_logger("chatbot.callback_handler")


class ToolLimitHook(HookProvider):
    """Hook provider to limit tool calls and prevent infinite loops."""

    def __init__(self, max_calls: int = 5):
        """
        Initialize the tool limit hook.

        Args:
            max_calls: Maximum number of tool calls allowed (default: 5)
        """
        self.tool_count = 0
        self.max_calls = max_calls
        logger.info(f"ToolLimitHook initialized with max_calls={max_calls}")

    def register_hooks(self, registry: Any, **kwargs: Any) -> None:
        """
        Register the hook with the agent's hook registry.

        Args:
            registry: The agent's hook registry
            **kwargs: Additional keyword arguments
        """
        registry.add_callback(BeforeToolCallEvent, self.before_tool_call)
        logger.info(f"ToolLimitHook registered with BeforeToolCallEvent")

    def before_tool_call(self, event: BeforeToolCallEvent) -> None:
        """
        Called before each tool call to enforce the limit.

        Args:
            event: The BeforeToolCallEvent containing tool call information
        """
        self.tool_count += 1
        tool_name = event.tool_use.get("name", "unknown")

        logger.info(f"🔧 Tool call #{self.tool_count}/{self.max_calls}: {tool_name}")

        # If limit reached, cancel the tool call
        if self.tool_count > self.max_calls:
            logger.warning(f"⛔ Tool call limit exceeded! Canceling tool: {tool_name}")
            event.cancel(
                f"Maximum tool call limit of {self.max_calls} reached. "
                f"Please provide your final answer based on the information gathered."
            )


class ToolLimitCallbackHandler:
    """Custom callback handler to track and display tool calls."""

    def __init__(self, max_calls: int = 5):
        """
        Initialize the callback handler.

        Args:
            max_calls: Maximum number of tool calls allowed (default: 5)
        """
        self.tool_count = 0
        self.max_calls = max_calls
        self.previous_tool_use = None
        logger.info(f"ToolLimitCallbackHandler initialized with max_calls={max_calls}")

    def __call__(self, **kwargs: Any) -> None:
        """
        Handle callback events from the agent.

        Args:
            **kwargs: Event data from the agent
        """
        # Track tool invocations for display purposes
        current_tool_use = kwargs.get("current_tool_use", {})

        if current_tool_use and current_tool_use.get("name"):
            # Only count unique tool uses (avoid counting same tool multiple times during streaming)
            if self.previous_tool_use != current_tool_use:
                self.previous_tool_use = current_tool_use
                self.tool_count += 1

        # Handle result event to check completion
        if "result" in kwargs:
            result = kwargs.get("result", {})
            stop_reason = result.stop_reason if hasattr(result, 'stop_reason') else 'unknown'
            logger.info(f"✅ Agent completed with stop_reason: {stop_reason}, total tools used: {self.tool_count}")

        # Handle force stop events
        if "force_stop_reason" in kwargs:
            reason = kwargs.get("force_stop_reason", "unknown")
            logger.warning(f"🛑 Event loop force-stopped: {reason}")
