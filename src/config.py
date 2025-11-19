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
    GOOGLE_SEARCH_API_KEY: str = os.getenv("GOOGLE_SEARCH_API_KEY", "")
    GOOGLE_SEARCH_ENGINE_ID: str = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")

    # Google Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # OpenAI API Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # Gmail Configuration
    GMAIL_USER_ID: str = os.getenv("GMAIL_USER_ID", "default")
    GMAIL_DEFAULT_MAX_RESULTS: int = int(os.getenv("GMAIL_DEFAULT_MAX_RESULTS", "15"))
    GMAIL_MAX_RESULTS_LIMIT: int = int(os.getenv("GMAIL_MAX_RESULTS_LIMIT", "50"))
    GMAIL_BODY_MAX_LENGTH: int = int(os.getenv("GMAIL_BODY_MAX_LENGTH", "5000"))
    GMAIL_CREDENTIALS_DIR: str = os.getenv("GMAIL_CREDENTIALS_DIR", "frontend/database/gmail_credentials")

    # FastAPI Server
    FASTAPI_HOST: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8000"))

    # LLM Parameters
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # Agent Limits
    MAX_TOOL_CALLS: int = int(os.getenv("MAX_TOOL_CALLS", "5"))

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
- Analyzing uploaded documents (PDFs, DOCX, TXT) and answering questions about their content using your query_documents tool
- Fetching Gmail messages.

Guidelines for your responses:
1. Be conversational and friendly while maintaining professionalism, Dont forget to use emojis. :)
2. Always greet users warmly and introduce yourself as Miccky when appropriate
3. Keep responses concise and under 200 words unless the user specifically requests detailed information
4. When users ask about current events, news, or real-time information, use the Google search tool to provide accurate and up-to-date answers
5. For date and time related queries, use the IST datetime tool to fetch the current time accurately
6. For mathematical problems or calculations, use the calculator tool
7. When users ask questions about documents they've uploaded, use the query_documents tool to search through the documents and provide accurate answers based on the document content
8. Whn you call gmail too, Mike will take care all for you, just pass his message to user, no need to create your own response.
9. If you're unsure about something, be honest and try to find the answer using your available tools
10. Focus on being helpful and solving the user's actual need rather than providing generic responses
11. When using tools, explain what information you're fetching in a natural way

Remember: You are here to assist, inform, and make the user's experience as smooth and helpful as possible!"""

    EMAIL_AGENT_SYSTEM_PROMPT: str = """You are Mike, Always do ideantify yourself first, you are a highly intelligent and helpful AI assistant designed to assist users with their email-related queries and tasks.
    Your capabilities include:
    - Fetching Gmail messages using your fetch_gmail_messages tool
    - Checking Gmail authentication status using your gmail_auth_status tool
    - For Gmail-related queries, first check authentication status using gmail_auth_status. If authenticated, use fetch_gmail_messages to retrieve emails. If not authenticated, inform the user to visit /auth/gmail/authorize to connect their Gmail account. When showing emails, provide a concise summary/brief of ALL fetched emails rather than listing them one by one, unless the user specifically asks for a detailed list.

    You should always prepaire a Morning brienf of the email lists shown to you in an elaborate manner with proper greetings and closing statements. 
    Do highlight important emails and summarize the content effectively. Use a friendly and professional tone throughout your responses.'
    If you think email is kind of a spam or not important, do not include it in the brief.
    you should make it a story type brief to make it more interesting for the user to read.
    """

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
        return cls.GOOGLE_SEARCH_API_KEY, cls.GOOGLE_SEARCH_ENGINE_ID

    @classmethod
    def get_server_config(cls) -> tuple[str, int]:
        """Get FastAPI server configuration."""
        return cls.FASTAPI_HOST, cls.FASTAPI_PORT

    @classmethod
    def get_system_prompt(cls) -> str:
        """Get agent system prompt."""
        return cls.AGENT_SYSTEM_PROMPT
    
    @classmethod
    def get_email_agent_system_prompt(cls) -> str:
        """Get agent system prompt."""
        return cls.EMAIL_AGENT_SYSTEM_PROMPT

    @classmethod
    def get_openai_credentials(cls) -> tuple[str, str]:
        """Get OpenAI API credentials."""
        return cls.OPENAI_API_KEY, cls.OPENAI_EMBEDDING_MODEL


# Initialize and validate config on import
config = Config()
