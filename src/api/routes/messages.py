"""Message endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Optional
from src.api.models import MessageCreate
from src.database import DatabaseManager
from src.logging_config import get_logger

logger = get_logger("chatbot.routes.messages")

router = APIRouter(prefix="/api/messages", tags=["messages"])

# Database manager will be injected by the app
_db_manager: Optional[DatabaseManager] = None


def set_db_manager(db_manager: DatabaseManager):
    """Inject database manager instance."""
    global _db_manager
    _db_manager = db_manager


@router.post("")
async def create_message(request: MessageCreate):
    """
    Add a message to a session.

    Args:
        request: MessageCreate containing session_id, role, and content

    Returns:
        Created message information
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    logger.info(f"Adding message to session {request.session_id}: {request.role}")

    try:
        # Verify session exists
        session = _db_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        message = _db_manager.add_message(
            session_id=request.session_id,
            role=request.role,
            content=request.content
        )
        return message
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create message: {str(e)}")


@router.get("/{session_id}")
async def get_messages(session_id: str):
    """
    Get all messages for a session.

    Args:
        session_id: Session identifier

    Returns:
        List of messages
    """
    if not _db_manager:
        raise HTTPException(status_code=500, detail="Database manager not initialized")

    try:
        # Verify session exists
        session = _db_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = _db_manager.get_messages(session_id)
        return {"messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")
