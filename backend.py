"""FastAPI backend for the chatbot application."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from src.agent.chatbot_agent import create_chatbot_agent
from src.agent.streaming_agent import create_streaming_response
from src.database import DatabaseManager
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
from pathlib import Path
import uuid

sys.path.append(str(Path(__file__).parent / "src"))
from src.config import Config
from src.logging_config import setup_logging

logger = setup_logging(Config.LOG_LEVEL, Config.LOG_TO_FILE, Config.LOG_TO_CONSOLE)

app = FastAPI(title="Chatbot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Initialize database manager
db_manager = DatabaseManager()

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []

class SessionCreate(BaseModel):
    title: str

class SessionUpdate(BaseModel):
    title: str

class MessageCreate(BaseModel):
    session_id: str
    role: str
    content: str


@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream agent responses with real-time tool execution updates."""
    limited_history = request.conversation_history[-10:] if len(request.conversation_history) > 10 else request.conversation_history

    return StreamingResponse(
        create_streaming_response(request.message, limited_history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Limit conversation history to last 10 messages (5 pairs of user-assistant)
    limited_history = request.conversation_history[-10:] if len(request.conversation_history) > 10 else request.conversation_history

    response_text = await create_chatbot_agent({
        "prompt": request.message,
        "conversation_history": limited_history
    })
    return {"response": response_text}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "llm_url": Config.LLAMA_CPP_URL}


# ============= Session Management Endpoints =============

@app.post("/api/sessions")
async def create_session(session: SessionCreate):
    """Create a new chat session."""
    try:
        session_id = str(uuid.uuid4())
        result = db_manager.create_session(session_id, session.title)
        return result
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions(limit: int = 50):
    """List all chat sessions."""
    try:
        sessions = db_manager.list_sessions(limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
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


@app.put("/api/sessions/{session_id}")
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


@app.delete("/api/sessions/{session_id}")
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


# ============= Message Management Endpoints =============

@app.post("/api/messages")
async def add_message(message: MessageCreate):
    """Add a message to a session."""
    try:
        result = db_manager.add_message(message.session_id, message.role, message.content)
        return result
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages/{session_id}")
async def get_messages(session_id: str):
    """Get all messages for a session."""
    try:
        messages = db_manager.get_messages(session_id)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    host, port = Config.get_server_config()
    uvicorn.run("backend:app", host=host, port=port, reload=True, reload_dirs=[".", "src", "frontend"])
