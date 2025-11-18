"""Session management endpoint routes."""
from fastapi import APIRouter, HTTPException
from src.database import DatabaseManager
from src.logging_config import get_logger
from ..models import SessionCreate, SessionUpdate
import uuid

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
logger = get_logger("chatbot.api.sessions")

# Database manager will be injected
db_manager = None


def set_db_manager(manager: DatabaseManager):
    """Set the database manager instance."""
    global db_manager
    db_manager = manager


@router.post("")
async def create_session(session: SessionCreate):
    """Create a new chat session."""
    try:
        session_id = str(uuid.uuid4())
        result = db_manager.create_session(session_id, session.title)
        return result
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_sessions(limit: int = 50):
    """List all chat sessions."""
    try:
        sessions = db_manager.list_sessions(limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_session(session_id: str, include_messages: bool = False):
    """Get a specific session."""
    try:
        if include_messages:
            session = db_manager.get_session_with_messages(session_id)
        else:
            session = db_manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}")
async def update_session(session_id: str, session: SessionUpdate):
    """Update session title."""
    try:
        success = db_manager.update_session_title(session_id, session.title)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    try:
        success = db_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
