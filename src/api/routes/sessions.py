"""Session CRUD endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Optional
from src.api.models import SessionCreate, SessionUpdate
from src.database import DatabaseManager
from src.logging_config import get_logger
import uuid

logger = get_logger("chatbot.routes.sessions")

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Database manager will be injected by the app
_db_manager: Optional[DatabaseManager] = None


def set_db_manager(db_manager: DatabaseManager):
    """Inject database manager instance."""
    global _db_manager
    _db_manager = db_manager


@router.post("")
async def create_session(request: SessionCreate):
    """
    Create a new chat session.

    Args:
        request: SessionCreate containing session title

    Returns:
        Created session information
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    session_id = str(uuid.uuid4())
    logger.info(f"Creating session: {session_id} with title: {request.title}")

    try:
        session = _db_manager.create_session(session_id, request.title)
        return session
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("")
async def list_sessions(limit: int = 50):
    """
    List all chat sessions ordered by last updated.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of sessions
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    try:
        sessions = _db_manager.list_sessions(limit=limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/{session_id}")
async def get_session(session_id: str, include_messages: bool = False):
    """
    Get a specific session by ID.

    Args:
        session_id: Session identifier
        include_messages: Whether to include messages in response

    Returns:
        Session information with optional messages
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    try:
        if include_messages:
            session = _db_manager.get_session_with_messages(session_id)
        else:
            session = _db_manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.put("/{session_id}")
async def update_session(session_id: str, request: SessionUpdate):
    """
    Update session title.

    Args:
        session_id: Session identifier
        request: SessionUpdate containing new title

    Returns:
        Success status
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    logger.info(f"Updating session {session_id} with title: {request.title}")

    try:
        success = _db_manager.update_session_title(session_id, request.title)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"success": True, "message": "Session updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and all its messages.

    Args:
        session_id: Session identifier

    Returns:
        Success status
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    logger.info(f"Deleting session: {session_id}")

    try:
        success = _db_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"success": True, "message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")
