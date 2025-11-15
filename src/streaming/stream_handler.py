"""Handles streaming chat responses from LlamaCpp."""
import json
import requests
from typing import List, Dict, Generator
from ..config import Config
from ..logging_config import get_logger

logger = get_logger("chatbot.streaming")


def stream_chat_response(message: str, conversation_history: List[Dict[str, str]] = None) -> Generator[str, None, None]:
    """
    Stream chat response from LlamaCpp server.

    Args:
        message: User message
        conversation_history: Previous conversation messages

    Yields:
        SSE formatted data chunks
    """
    try:
        messages = [*(conversation_history or []), {"role": "user", "content": message}]

        response = requests.post(
            f"{Config.LLAMA_CPP_URL}/v1/chat/completions",
            json={"messages": messages, "temperature": Config.LLM_TEMPERATURE, "max_tokens": Config.LLM_MAX_TOKENS, "stream": True},
            stream=True,
            timeout=120
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line and (text := line.decode('utf-8')).startswith('data: '):
                if (data_str := text[6:].strip()) == '[DONE]':
                    break
                try:
                    if content := json.loads(data_str).get("choices", [{}])[0].get("delta", {}).get("content", ""):
                        yield f"data: {json.dumps({'chunk': content, 'done': False})}\n\n"
                except json.JSONDecodeError:
                    continue

        yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"

    except Exception as e:
        logger.error(f"Chat streaming failed: {str(e)}", exc_info=True)
        yield f"data: {json.dumps({'chunk': f'Error: {str(e)}', 'done': True, 'error': True})}\n\n"
