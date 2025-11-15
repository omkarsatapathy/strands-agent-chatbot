"""FastAPI backend for the chatbot application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))
from src.config import Config
from src.logging_config import setup_logging
from src.streaming import stream_chat_response

logger = setup_logging(Config.LOG_LEVEL, Config.LOG_TO_FILE, Config.LOG_TO_CONSOLE)

app = FastAPI(title="Chatbot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="frontend"), name="static")

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []


@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_chat_response(request.message, request.conversation_history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "llm_url": Config.LLAMA_CPP_URL}


if __name__ == "__main__":
    import uvicorn
    host, port = Config.get_server_config()
    uvicorn.run("backend:app", host=host, port=port, reload=True, reload_dirs=[".", "src", "frontend"])
