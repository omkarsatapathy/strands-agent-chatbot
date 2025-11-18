"""Message management endpoint routes."""
from fastapi import APIRouter, HTTPException
from src.database import DatabaseManager
from src.logging_config import get_logger
from ..models import MessageCreate

router = APIRouter(prefix="/api/messages", tags=["messages"])
logger = get_logger("chatbot.api.messages")

# Database manager will be injected
db_manager = None


def set_db_manager(manager: DatabaseManager):
    """Set the database manager instance."""
    global db_manager
    db_manager = manager


@router.post("")
async def add_message(message: MessageCreate):
    """Add a message to a session."""
    try:
        result = db_manager.add_message(message.session_id, message.role, message.content)
        return result
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_messages(session_id: str):
    """Get all messages for a session."""
    try:
        messages = db_manager.get_messages(session_id)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
