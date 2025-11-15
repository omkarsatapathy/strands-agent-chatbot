"""FastAPI backend for the chatbot application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
import sys
from pathlib import Path
import json
import requests

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.config import Config
from src.logging_config import setup_logging, get_logger

# Setup logging
logger = setup_logging(
    log_level=Config.LOG_LEVEL,
    log_to_file=Config.LOG_TO_FILE,
    log_to_console=Config.LOG_TO_CONSOLE
)

app = FastAPI(title="Chatbot API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Request model
class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []


@app.get("/")
async def read_root():
    """Serve the frontend."""
    return FileResponse("frontend/index.html")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint with streaming support.

    Args:
        request: ChatRequest containing the user message

    Returns:
        StreamingResponse with SSE (Server-Sent Events)
    """
    def generate_stream():
        """Generate real token-by-token streaming response."""
        try:
            logger.info(f"Processing chat request: {request.message}")

            # Build messages
            messages = []
            messages.extend(request.conversation_history)
            messages.append({"role": "user", "content": request.message})

            # Direct streaming from LlamaCpp
            payload = {
                "messages": messages,
                "temperature": Config.LLM_TEMPERATURE,
                "max_tokens": Config.LLM_MAX_TOKENS,
                "stream": True
            }

            logger.info(f"Calling LlamaCpp at {Config.LLAMA_CPP_URL}")

            response = requests.post(
                f"{Config.LLAMA_CPP_URL}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=120
            )
            response.raise_for_status()

            # Stream tokens as they arrive
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'chunk': content, 'done': False})}\n\n"
                        except json.JSONDecodeError:
                            continue

            # Send completion signal
            yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"
            logger.info("Chat request completed")

        except Exception as e:
            logger.error(f"Chat request failed: {str(e)}", exc_info=True)
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'chunk': error_msg, 'done': True, 'error': True})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "llm_url": Config.LLAMA_CPP_URL
    }


if __name__ == "__main__":
    import uvicorn
    host, port = Config.get_server_config()

    logger.info(f"Starting FastAPI server on {host}:{port}")

    uvicorn.run(
        "backend:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[".", "src", "frontend"]
    )
