"""Agent configuration - Model and tools setup."""
from typing import List
from strands import Agent, tool
from strands.models.llamacpp import LlamaCppModel
from strands_tools import calculator
from ..config import Config
from ..tools.google_search import google_search_with_context
from ..tools.datetime_ist import get_current_datetime_ist
from ..tools.document_rag import query_documents


def create_llm_model():
    """Create and configure the LLM model.

    Returns:
        LlamaCppModel: Configured LLM model instance
    """
    return LlamaCppModel(
        base_url=Config.LLAMA_CPP_URL,
        model_id="default",
        params={
            "max_tokens": Config.LLM_MAX_TOKENS,
            "temperature": Config.LLM_TEMPERATURE,
            "repeat_penalty": 1.1,
        }
    )


def build_tools_list(session_id: str = None) -> List:
    """Build the list of tools available to the agent.

    Args:
        session_id: Optional session ID for document-specific tools

    Returns:
        List of tools available to the agent
    """
    # Base tools available to all agents
    tools = [
        calculator,
        google_search_with_context,
        get_current_datetime_ist
    ]

    # Add document query tool if session is provided
    if session_id:
        # Create a wrapper function that binds session_id
        def query_documents_wrapper(query: str) -> dict:
            """Query uploaded documents for information using RAG.

            Use this tool when the user asks questions about their uploaded documents.

            Args:
                query: The question about the documents

            Returns:
                Dictionary with answer from documents
            """
            return query_documents(query=query, session_id=session_id)

        # Register as a tool
        query_docs_tool = tool(query_documents_wrapper)
        tools.append(query_docs_tool)

    return tools


def create_agent(session_id: str = None, history_messages: List = None, hooks: List = None):
    """Create and configure the Strands agent.

    Args:
        session_id: Optional session ID for document-specific tools
        history_messages: Conversation history in Strands format
        hooks: List of hooks to attach to the agent

    Returns:
        Configured Agent instance
    """
    model = create_llm_model()
    tools = build_tools_list(session_id)

    return Agent(
        model=model,
        tools=tools,
        system_prompt=Config.get_system_prompt(),
        messages=history_messages or [],
        hooks=hooks or [],
        callback_handler=None  # No callback handler needed with stream_async
    )
