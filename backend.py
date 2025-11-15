"""FastAPI backend for the chatbot application."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import sys
from pathlib import Path
import time
import json

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.agent.chatbot_agent import create_chatbot_agent
from src.tools.google_search import google_search, google_image_search
from src.config import Config
from src.logging_config import setup_logging, get_logger

# Setup logging
logger = setup_logging(
    log_level=Config.LOG_LEVEL,
    log_to_file=Config.LOG_TO_FILE,
    log_to_console=Config.LOG_TO_CONSOLE
)


app = FastAPI(title="Chatbot API", version="1.0.0")

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()

    # Log request
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown"
            }
        }
    )

    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} - Status: {response.status_code}",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}s"
                }
            }
        )

        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path}",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "process_time": f"{process_time:.3f}s"
                }
            },
            exc_info=True
        )
        raise

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

logger.info("FastAPI application initialized")


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []


class ChatResponse(BaseModel):
    response: str
    error: str = None


class SearchRequest(BaseModel):
    query: str
    num_results: int = 5
    search_type: str = "web"  # "web" or "image"


# Initialize agent
agent = None


def get_agent():
    """Lazy initialization of the agent."""
    global agent
    if agent is None:
        logger.info("Initializing chatbot agent")
        # Create agent using config values
        agent = create_chatbot_agent()
        logger.info("Chatbot agent initialized successfully")
    return agent


@app.get("/")
async def read_root():
    """Serve the frontend."""
    logger.debug("Serving frontend index.html")
    return FileResponse("frontend/index.html")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint with REAL streaming support from LlamaCpp.

    Args:
        request: ChatRequest containing the user message and conversation history

    Returns:
        StreamingResponse with SSE (Server-Sent Events)
    """
    async def generate_stream():
        """Generate streaming response from LlamaCpp."""
        try:
            logger.info(
                "Processing streaming chat request",
                extra={"extra_data": {
                    "message_length": len(request.message),
                    "history_length": len(request.conversation_history)
                }}
            )

            agent_instance = get_agent()

            # Call the agent with the message
            system_prompt = "You are a helpful AI assistant. You can search the web and help users with various tasks."

            # Use REAL streaming from LlamaCpp with conversation history
            for chunk in agent_instance.chat_stream(
                request.message,
                system_prompt=system_prompt,
                conversation_history=request.conversation_history
            ):
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

            # Send completion signal
            yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"

            logger.info("Streaming chat request completed")

        except Exception as e:
            logger.error(
                "Streaming chat request failed",
                extra={"extra_data": {"error": str(e)}},
                exc_info=True
            )
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


@app.post("/api/search")
async def search(request: SearchRequest):
    """
    Search endpoint for Google Custom Search.

    Args:
        request: SearchRequest containing query and search parameters

    Returns:
        Search results
    """
    try:
        logger.info(
            f"Processing search request: {request.search_type}",
            extra={"extra_data": {"query": request.query, "num_results": request.num_results}}
        )

        if request.search_type == "image":
            results = google_image_search(request.query, request.num_results)
        else:
            results = google_search(request.query, request.num_results)

        logger.info(
            "Search request completed",
            extra={"extra_data": {"results_count": len(results)}}
        )

        return {"results": results}

    except Exception as e:
        logger.error(
            "Search request failed",
            extra={"extra_data": {"query": request.query, "error": str(e)}},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "llm_url": Config.LLAMA_CPP_URL
    }


if __name__ == "__main__":
    import uvicorn
    host, port = Config.get_server_config()

    logger.info(
        f"Starting FastAPI server",
        extra={
            "extra_data": {
                "host": host,
                "port": port,
                "llm_url": Config.LLAMA_CPP_URL,
                "reload": True
            }
        }
    )

    uvicorn.run(
        "backend:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[".", "src", "frontend"]
    )
