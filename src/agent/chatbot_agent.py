"""Simple LlamaCPP integration without Strands agent."""
from typing import List, Dict, Any, Optional
import requests
from ..config import Config
from ..logging_config import get_logger

logger = get_logger("chatbot.agent")


class SimpleLlamaCppClient:
    """Simple client for llama.cpp server."""

    def __init__(self, base_url: Optional[str] = None, temperature: Optional[float] = None):
        """
        Initialize LlamaCpp client.

        Args:
            base_url: The URL of the llama.cpp server (defaults to config)
            temperature: Sampling temperature (defaults to config)
        """
        self.base_url = (base_url or Config.LLAMA_CPP_URL).rstrip('/')
        self.temperature = temperature or Config.LLM_TEMPERATURE
        self.conversation_history: List[Dict[str, str]] = []

        logger.info(
            "LlamaCpp client initialized",
            extra={
                "extra_data": {
                    "base_url": self.base_url,
                    "temperature": self.temperature,
                    "max_tokens": Config.LLM_MAX_TOKENS
                }
            }
        )

    def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a chat message to the LlamaCpp server.

        Args:
            message: User message
            system_prompt: Optional system prompt

        Returns:
            Response text from the LLM
        """
        logger.info(
            "Starting chat interaction",
            extra={
                "extra_data": {
                    "message_length": len(message),
                    "has_system_prompt": system_prompt is not None,
                    "history_length": len(self.conversation_history)
                }
            }
        )

        # Build messages array
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            logger.debug(
                "Added system prompt",
                extra={"extra_data": {"system_prompt_length": len(system_prompt)}}
            )

        # Add conversation history
        messages.extend(self.conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": message})

        payload = {
            "messages": messages,
            "model": "default",
            "temperature": self.temperature,
            "max_tokens": Config.LLM_MAX_TOKENS,
        }

        logger.debug(
            "Sending request to LlamaCpp server",
            extra={
                "extra_data": {
                    "url": f"{self.base_url}/v1/chat/completions",
                    "total_messages": len(messages),
                    "temperature": self.temperature
                }
            }
        )

        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )

            logger.debug(
                "Received response from LlamaCpp",
                extra={"extra_data": {"status_code": response.status_code}}
            )

            response.raise_for_status()
            data = response.json()

            logger.debug(
                "Parsed LlamaCpp response",
                extra={"extra_data": {"response_keys": list(data.keys())}}
            )

            # Extract content from OpenAI-style response
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": content})

            # Keep only last 10 messages to avoid context overflow
            if len(self.conversation_history) > 20:
                logger.debug("Trimming conversation history to last 20 messages")
                self.conversation_history = self.conversation_history[-20:]

            logger.info(
                "Chat interaction completed successfully",
                extra={
                    "extra_data": {
                        "response_length": len(content),
                        "new_history_length": len(self.conversation_history)
                    }
                }
            )

            return content

        except requests.exceptions.Timeout as e:
            logger.error(
                "LlamaCpp request timeout",
                extra={"extra_data": {"timeout": 60, "url": self.base_url}},
                exc_info=True
            )
            return f"Error: Request timeout after 60s - {str(e)}"
        except requests.exceptions.HTTPError as e:
            logger.error(
                "HTTP error from LlamaCpp server",
                extra={
                    "extra_data": {
                        "status_code": e.response.status_code,
                        "url": self.base_url
                    }
                },
                exc_info=True
            )
            return f"Error: HTTP {e.response.status_code} - {str(e)}"
        except Exception as e:
            logger.error(
                "Unexpected error calling LlamaCpp",
                extra={"extra_data": {"error_type": type(e).__name__, "url": self.base_url}},
                exc_info=True
            )
            return f"Error calling LlamaCpp: {str(e)}"

    def chat_stream(self, message: str, system_prompt: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None):
        """
        Send a chat message and stream the response from LlamaCpp server.

        Args:
            message: User message
            system_prompt: Optional system prompt
            conversation_history: Optional conversation history to use instead of self.conversation_history

        Yields:
            Chunks of text from the LLM as they arrive
        """
        # Use provided conversation history or fall back to self.conversation_history
        history_to_use = conversation_history if conversation_history is not None else self.conversation_history

        logger.info(
            "Starting streaming chat interaction",
            extra={
                "extra_data": {
                    "message_length": len(message),
                    "has_system_prompt": system_prompt is not None,
                    "history_length": len(history_to_use)
                }
            }
        )

        # Build messages array
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        messages.extend(history_to_use)

        # Add current user message
        messages.append({"role": "user", "content": message})

        payload = {
            "messages": messages,
            "model": "default",
            "temperature": self.temperature,
            "max_tokens": Config.LLM_MAX_TOKENS,
            "stream": True  # Enable streaming
        }

        logger.debug(
            "Sending streaming request to LlamaCpp server",
            extra={
                "extra_data": {
                    "url": f"{self.base_url}/v1/chat/completions",
                    "total_messages": len(messages),
                    "stream": True
                }
            }
        )

        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120,
                stream=True  # Stream the response
            )

            response.raise_for_status()

            full_content = ""

            # Process streaming response
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')

                    # SSE format: data: {...}
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]  # Remove 'data: ' prefix

                        # Check for [DONE] signal
                        if data_str.strip() == '[DONE]':
                            break

                        try:
                            import json
                            data = json.loads(data_str)

                            # Extract delta content from streaming response
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content_chunk = delta.get("content", "")

                            if content_chunk:
                                full_content += content_chunk
                                yield content_chunk

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON: {data_str}")
                            continue

            # Update conversation history only if using internal history (not provided externally)
            if conversation_history is None:
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": full_content})

                # Keep only last 20 messages
                if len(self.conversation_history) > 20:
                    logger.debug("Trimming conversation history to last 20 messages")
                    self.conversation_history = self.conversation_history[-20:]

            logger.info(
                "Streaming chat interaction completed",
                extra={
                    "extra_data": {
                        "response_length": len(full_content),
                        "history_used_length": len(history_to_use)
                    }
                }
            )

        except Exception as e:
            logger.error(
                "Error during streaming chat",
                extra={"extra_data": {"error_type": type(e).__name__}},
                exc_info=True
            )
            yield f"Error: {str(e)}"

    def reset_conversation(self):
        """Reset the conversation history."""
        logger.info(
            "Resetting conversation history",
            extra={"extra_data": {"previous_length": len(self.conversation_history)}}
        )
        self.conversation_history = []


def create_chatbot_agent(
    llm_url: Optional[str] = None,
    temperature: Optional[float] = None
) -> SimpleLlamaCppClient:
    """
    Create a simple chatbot client with LlamaCpp backend.

    Args:
        llm_url: URL of the llama.cpp server (defaults to config)
        temperature: Sampling temperature (defaults to config)

    Returns:
        Configured SimpleLlamaCppClient instance
    """
    logger.info(
        "Creating new chatbot agent",
        extra={
            "extra_data": {
                "llm_url": llm_url or Config.LLAMA_CPP_URL,
                "temperature": temperature or Config.LLM_TEMPERATURE
            }
        }
    )
    return SimpleLlamaCppClient(base_url=llm_url, temperature=temperature)
