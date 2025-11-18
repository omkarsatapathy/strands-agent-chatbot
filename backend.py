"""FastAPI backend for the chatbot application."""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from src.agent.streaming_agent import create_streaming_response
from src.database import DatabaseManager
from src.tools.document_rag import get_rag_manager
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
from pathlib import Path
import uuid
import os
import shutil

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
    session_id: Optional[str] = None

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
        create_streaming_response(
            request.message,
            limited_history,
            session_id=request.session_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


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


# ============= Document/PDF Upload Endpoints =============

@app.post("/api/upload")
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


@app.get("/api/documents/{session_id}")
async def get_session_documents(session_id: str):
    """Get all documents for a session."""
    try:
        documents = db_manager.get_documents(session_id)
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents/show-in-folder")
async def show_document_in_folder(request: dict):
    """Open file in Finder/Explorer."""
    import subprocess
    import platform

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


if __name__ == "__main__":
    import uvicorn
    host, port = Config.get_server_config()
    uvicorn.run(
        "backend:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[".", "src", "frontend"],
        log_level="warning"  # Reduce log verbosity (only warnings and errors)
    )
