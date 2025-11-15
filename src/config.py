"""Configuration management for the chatbot application."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration."""

    # LlamaCpp Server
    LLAMA_CPP_URL: str = os.getenv("LLAMA_CPP_URL", "http://127.0.0.1:8033")

    # Google Custom Search API
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_SEARCH_ENGINE_ID: str = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")

    # FastAPI Server
    FASTAPI_HOST: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8000"))

    # LLM Parameters
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "True").lower() in ("true", "1", "yes")
    LOG_TO_CONSOLE: bool = os.getenv("LOG_TO_CONSOLE", "True").lower() in ("true", "1", "yes")

    # Agent System Prompt
    AGENT_SYSTEM_PROMPT: str = """You are Miccky, a highly intelligent and helpful AI assistant designed to provide accurate, concise, and relevant information to users.

Your capabilities include:
- Performing mathematical calculations using your calculator tool
- Searching the web for latest news, information, and updates using your Google search tool
- Providing current date and time in Indian Standard Time (IST) using your datetime tool

Guidelines for your responses:
1. Be conversational and friendly while maintaining professionalism, Dont forget to use emojis. :)
2. Always greet users warmly and introduce yourself as Miccky when appropriate
3. Keep responses concise and under 200 words unless the user specifically requests detailed information
4. When users ask about current events, news, or real-time information, use the Google search tool to provide accurate and up-to-date answers
5. For date and time related queries, use the IST datetime tool to fetch the current time accurately
6. For mathematical problems or calculations, use the calculator tool
7. If you're unsure about something, be honest and try to find the answer using your available tools
8. Focus on being helpful and solving the user's actual need rather than providing generic responses
9. When using tools, explain what information you're fetching in a natural way

Remember: You are here to assist, inform, and make the user's experience as smooth and helpful as possible!"""

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY not set in .env file")
            return False
        if not cls.GOOGLE_SEARCH_ENGINE_ID:
            print("Warning: GOOGLE_SEARCH_ENGINE_ID not set in .env file")
            return False
        return True

    @classmethod
    def get_llama_cpp_url(cls) -> str:
        """Get LlamaCpp server URL."""
        return cls.LLAMA_CPP_URL

    @classmethod
    def get_google_credentials(cls) -> tuple[str, str]:
        """Get Google API credentials."""
        return cls.GOOGLE_API_KEY, cls.GOOGLE_SEARCH_ENGINE_ID

    @classmethod
    def get_server_config(cls) -> tuple[str, int]:
        """Get FastAPI server configuration."""
        return cls.FASTAPI_HOST, cls.FASTAPI_PORT

    @classmethod
    def get_system_prompt(cls) -> str:
        """Get agent system prompt."""
        return cls.AGENT_SYSTEM_PROMPT


# Initialize and validate config on import
config = Config()
