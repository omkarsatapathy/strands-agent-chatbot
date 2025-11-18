"""Document RAG tool using LlamaIndex for PDF/document analysis."""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from strands import tool
from ..config import Config
from ..logging_config import get_logger

logger = get_logger("chatbot.tools.document_rag")

# Global storage for RAG managers per session
_rag_managers: Dict[str, 'DocumentRAGManager'] = {}


class DocumentRAGManager:
    """Manages document indexing and querying for a specific session."""

    def __init__(self, session_id: str):
        """Initialize RAG manager for a session."""
        self.session_id = session_id
        self.vector_db_path = Path("vector_db") / session_id
        self.upload_dir = Path("uploads") / session_id
        self.index: Optional[VectorStoreIndex] = None

        # Ensure directories exist
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        # Configure LlamaIndex settings
        api_key, embedding_model = Config.get_openai_credentials()
        Settings.embed_model = OpenAIEmbedding(
            model=embedding_model,
            api_key=api_key
        )
        Settings.llm = OpenAI(
            model="gpt-3.5-turbo",
            api_key=api_key,
            temperature=0.1
        )

        logger.info(
            f"Initialized DocumentRAGManager",
            extra={"extra_data": {
                "session_id": session_id,
                "vector_db_path": str(self.vector_db_path),
                "upload_dir": str(self.upload_dir)
            }}
        )

    def load_existing_index(self) -> bool:
        """Load existing vector index if available."""
        try:
            if (self.vector_db_path / "docstore.json").exists():
                logger.info(
                    f"Loading existing vector index",
                    extra={"extra_data": {"session_id": self.session_id}}
                )
                storage_context = StorageContext.from_defaults(
                    persist_dir=str(self.vector_db_path)
                )
                self.index = load_index_from_storage(storage_context)
                logger.info(
                    f"Successfully loaded existing index",
                    extra={"extra_data": {"session_id": self.session_id}}
                )
                return True
            return False
        except Exception as e:
            logger.error(
                f"Error loading existing index",
                extra={"extra_data": {"session_id": self.session_id, "error": str(e)}},
                exc_info=True
            )
            return False

    def add_documents(self, file_paths: list[str]) -> Dict[str, Any]:
        """
        Add new documents to the index.

        Args:
            file_paths: List of file paths to add

        Returns:
            Status dictionary with success/error info
        """
        try:
            logger.info(
                f"Adding documents to index",
                extra={"extra_data": {
                    "session_id": self.session_id,
                    "num_files": len(file_paths)
                }}
            )

            # Load documents
            documents = []
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    logger.warning(
                        f"File not found",
                        extra={"extra_data": {"file_path": file_path}}
                    )
                    continue

                # Use SimpleDirectoryReader for single file
                file_dir = os.path.dirname(file_path)
                filename = os.path.basename(file_path)

                reader = SimpleDirectoryReader(
                    input_dir=file_dir,
                    required_exts=[os.path.splitext(filename)[1]],
                    filename_as_id=True
                )
                docs = reader.load_data()
                documents.extend(docs)

                logger.debug(
                    f"Loaded document",
                    extra={"extra_data": {
                        "filename": filename,
                        "num_chunks": len(docs)
                    }}
                )

            if not documents:
                return {
                    "success": False,
                    "error": "No valid documents found to index"
                }

            # Create or update index
            if self.index is None:
                # Try to load existing index first
                if not self.load_existing_index():
                    # Create new index
                    logger.info(
                        f"Creating new vector index",
                        extra={"extra_data": {
                            "session_id": self.session_id,
                            "num_documents": len(documents)
                        }}
                    )
                    self.index = VectorStoreIndex.from_documents(documents)
                else:
                    # Add to existing index
                    logger.info(
                        f"Adding to existing index",
                        extra={"extra_data": {
                            "session_id": self.session_id,
                            "num_new_documents": len(documents)
                        }}
                    )
                    for doc in documents:
                        self.index.insert(doc)
            else:
                # Index already loaded, just insert new documents
                logger.info(
                    f"Inserting documents into loaded index",
                    extra={"extra_data": {
                        "session_id": self.session_id,
                        "num_new_documents": len(documents)
                    }}
                )
                for doc in documents:
                    self.index.insert(doc)

            # Persist index
            self.index.storage_context.persist(persist_dir=str(self.vector_db_path))

            logger.info(
                f"Successfully indexed documents",
                extra={"extra_data": {
                    "session_id": self.session_id,
                    "num_documents": len(documents),
                    "vector_db_path": str(self.vector_db_path)
                }}
            )

            return {
                "success": True,
                "num_documents": len(documents),
                "vector_db_path": str(self.vector_db_path)
            }

        except Exception as e:
            logger.error(
                f"Error adding documents to index",
                extra={"extra_data": {
                    "session_id": self.session_id,
                    "error": str(e)
                }},
                exc_info=True
            )
            return {
                "success": False,
                "error": f"Failed to index documents: {str(e)}"
            }

    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Query the document index.

        Args:
            query_text: The query string

        Returns:
            Query result dictionary
        """
        try:
            # Load index if not already loaded
            if self.index is None:
                if not self.load_existing_index():
                    return {
                        "success": False,
                        "error": "No documents have been indexed yet. Please upload a document first."
                    }

            logger.info(
                f"Querying document index",
                extra={"extra_data": {
                    "session_id": self.session_id,
                    "query": query_text
                }}
            )

            # Create query engine
            query_engine = self.index.as_query_engine(
                similarity_top_k=3,
                response_mode="tree_summarize"
            )

            # Execute query
            response = query_engine.query(query_text)

            logger.info(
                f"Query completed successfully",
                extra={"extra_data": {
                    "session_id": self.session_id,
                    "response_length": len(str(response))
                }}
            )

            return {
                "success": True,
                "answer": str(response),
                "source_nodes": len(response.source_nodes) if hasattr(response, 'source_nodes') else 0
            }

        except Exception as e:
            logger.error(
                f"Error querying document index",
                extra={"extra_data": {
                    "session_id": self.session_id,
                    "query": query_text,
                    "error": str(e)
                }},
                exc_info=True
            )
            return {
                "success": False,
                "error": f"Failed to query documents: {str(e)}"
            }


def get_rag_manager(session_id: str) -> DocumentRAGManager:
    """Get or create RAG manager for a session."""
    if session_id not in _rag_managers:
        _rag_managers[session_id] = DocumentRAGManager(session_id)
    return _rag_managers[session_id]


@tool
def query_documents(query: str, session_id: str) -> Dict[str, Any]:
    """
    Strands tool: Query uploaded documents for information using RAG.

    This tool allows you to search through uploaded PDF and document files
    to find relevant information and answer questions based on the document content.

    Use this tool when the user asks questions about their uploaded documents or
    wants to extract information from PDFs they've shared.

    Args:
        query: The question or search query about the documents
        session_id: The current chat session ID

    Returns:
        Dictionary with the answer from the documents or error message
    """
    logger.info(
        f"query_documents tool called",
        extra={"extra_data": {
            "query": query,
            "session_id": session_id
        }}
    )

    try:
        rag_manager = get_rag_manager(session_id)
        result = rag_manager.query(query)

        if result["success"]:
            logger.info(
                f"Document query successful",
                extra={"extra_data": {
                    "session_id": session_id,
                    "query": query,
                    "source_nodes": result.get("source_nodes", 0)
                }}
            )
            return {
                "answer": result["answer"],
                "sources": result.get("source_nodes", 0)
            }
        else:
            logger.warning(
                f"Document query failed",
                extra={"extra_data": {
                    "session_id": session_id,
                    "error": result.get("error")
                }}
            )
            return {
                "error": result.get("error", "Unknown error occurred")
            }

    except Exception as e:
        logger.error(
            f"Unexpected error in query_documents tool",
            extra={"extra_data": {
                "session_id": session_id,
                "query": query,
                "error": str(e)
            }},
            exc_info=True
        )
        return {
            "error": f"Failed to query documents: {str(e)}"
        }
