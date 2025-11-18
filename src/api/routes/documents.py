"""Document upload and management endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, List
from pathlib import Path
import shutil
from src.database import DatabaseManager
from src.tools.document_rag import get_rag_manager
from src.logging_config import get_logger

logger = get_logger("chatbot.routes.documents")

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Database manager will be injected by the app
_db_manager: Optional[DatabaseManager] = None


def set_db_manager(db_manager: DatabaseManager):
    """Inject database manager instance."""
    global _db_manager
    _db_manager = db_manager


@router.post("/upload")
async def upload_documents(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Upload documents for a session and index them for RAG.

    Args:
        session_id: Session identifier
        files: List of files to upload

    Returns:
        Upload status with indexed document information
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    logger.info(f"Uploading {len(files)} documents for session {session_id}")

    try:
        # Verify session exists
        session = _db_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Create upload directory for this session
        upload_dir = Path("uploads") / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = []
        file_paths = []

        # Save uploaded files
        for file in files:
            if not file.filename:
                continue

            file_path = upload_dir / file.filename
            file_size = 0

            # Save file to disk
            with file_path.open("wb") as buffer:
                content = await file.read()
                file_size = len(content)
                buffer.write(content)

            logger.info(f"Saved file: {file.filename} ({file_size} bytes)")

            # Add document record to database
            doc_record = _db_manager.add_document(
                session_id=session_id,
                filename=file.filename,
                file_path=str(file_path),
                file_size=file_size
            )

            uploaded_files.append(doc_record)
            file_paths.append(str(file_path))

        # Index documents using RAG manager
        logger.info(f"Indexing {len(file_paths)} documents for session {session_id}")
        rag_manager = get_rag_manager(session_id)
        index_result = rag_manager.add_documents(file_paths)

        if not index_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to index documents: {index_result.get('error')}"
            )

        # Update session with vector DB path
        vector_db_path = index_result.get("vector_db_path")
        _db_manager.update_session_vector_db(session_id, vector_db_path)

        logger.info(
            f"Successfully uploaded and indexed {len(uploaded_files)} documents",
            extra={"extra_data": {
                "session_id": session_id,
                "num_documents": len(uploaded_files),
                "vector_db_path": vector_db_path
            }}
        )

        return {
            "success": True,
            "message": f"Successfully uploaded and indexed {len(uploaded_files)} document(s)",
            "documents": uploaded_files,
            "indexed_documents": index_result.get("num_documents", 0),
            "vector_db_path": vector_db_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload documents: {str(e)}")


@router.get("/{session_id}")
async def get_documents(session_id: str):
    """
    Get all documents for a session.

    Args:
        session_id: Session identifier

    Returns:
        List of documents with metadata
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    try:
        # Verify session exists
        session = _db_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        documents = _db_manager.get_documents(session_id)

        return {
            "session_id": session_id,
            "documents": documents,
            "count": len(documents),
            "has_vector_db": session.get("has_documents", False),
            "vector_db_path": session.get("vector_db_path")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {str(e)}")


@router.post("/{session_id}/query")
async def query_documents(session_id: str, query: str = Form(...)):
    """
    Query documents using RAG for a specific session.

    Args:
        session_id: Session identifier
        query: Query string to search documents

    Returns:
        Query results with answer and sources
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    logger.info(f"Querying documents for session {session_id}: {query}")

    try:
        # Verify session exists
        session = _db_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Check if session has documents
        if not session.get("has_documents"):
            raise HTTPException(
                status_code=400,
                detail="No documents uploaded for this session"
            )

        # Query documents using RAG manager
        rag_manager = get_rag_manager(session_id)
        result = rag_manager.query(query)

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Query failed: {result.get('error')}"
            )

        logger.info(
            f"Document query successful",
            extra={"extra_data": {
                "session_id": session_id,
                "query": query,
                "source_nodes": result.get("source_nodes", 0)
            }}
        )

        return {
            "success": True,
            "query": query,
            "answer": result.get("answer"),
            "source_nodes": result.get("source_nodes", 0)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to query documents: {str(e)}")
