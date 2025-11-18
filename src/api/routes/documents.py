"""Document/PDF upload endpoint routes."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from src.database import DatabaseManager
from src.tools.document_rag import get_rag_manager
from src.logging_config import get_logger
from pathlib import Path
import os
import shutil
import subprocess
import platform

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = get_logger("chatbot.api.documents")

# Database manager will be injected
db_manager = None


def set_db_manager(manager: DatabaseManager):
    """Set the database manager instance."""
    global db_manager
    db_manager = manager


@router.post("/upload", prefix="/api")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """Upload a PDF/document file and index it for RAG."""
    try:
        logger.info(f"Upload request: {file.filename} for session {session_id}")

        # Validate file type
        allowed_extensions = {'.pdf', '.txt', '.docx', '.doc'}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Create session upload directory
        upload_dir = Path("uploads") / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)

        logger.info(f"File saved: {file_path} ({file_size} bytes)")

        # Add to database
        db_manager.add_document(
            session_id=session_id,
            filename=file.filename,
            file_path=str(file_path),
            file_size=file_size
        )

        # Index document using RAG manager
        rag_manager = get_rag_manager(session_id)
        index_result = rag_manager.add_documents([str(file_path)])

        if not index_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to index document: {index_result.get('error')}"
            )

        # Update session with vector DB path
        vector_db_path = index_result.get("vector_db_path")
        db_manager.update_session_vector_db(session_id, vector_db_path)

        logger.info(f"Document indexed successfully: {file.filename}")

        return {
            "success": True,
            "filename": file.filename,
            "file_size": file_size,
            "indexed": True,
            "message": f"Successfully uploaded and indexed {file.filename}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_session_documents(session_id: str):
    """Get all documents for a session."""
    try:
        documents = db_manager.get_documents(session_id)
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/show-in-folder")
async def show_document_in_folder(request: dict):
    """Open file in Finder/Explorer."""
    try:
        file_path = request.get('file_path')
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        system = platform.system()

        if system == 'Darwin':  # macOS
            subprocess.run(['open', '-R', file_path])
        elif system == 'Windows':
            subprocess.run(['explorer', '/select,', os.path.abspath(file_path)])
        elif system == 'Linux':
            # Open parent directory
            subprocess.run(['xdg-open', os.path.dirname(os.path.abspath(file_path))])

        logger.info(f"Opened file in folder: {file_path}")
        return {"success": True, "message": "File opened in folder"}

    except Exception as e:
        logger.error(f"Error opening file in folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))
