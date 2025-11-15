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

sys.path.append(str(Path(__file__).parent / "src"))
from src.config import Config
from src.logging_config import setup_logging, get_logger

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
    def generate_stream():
        try:
            messages = [*request.conversation_history, {"role": "user", "content": request.message}]

            response = requests.post(
                f"{Config.LLAMA_CPP_URL}/v1/chat/completions",
                json={"messages": messages, "temperature": Config.LLM_TEMPERATURE, "max_tokens": Config.LLM_MAX_TOKENS, "stream": True},
                stream=True,
                timeout=120
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line and (text := line.decode('utf-8')).startswith('data: '):
                    if (data_str := text[6:].strip()) == '[DONE]':
                        break
                    try:
                        if content := json.loads(data_str).get("choices", [{}])[0].get("delta", {}).get("content", ""):
                            yield f"data: {json.dumps({'chunk': content, 'done': False})}\n\n"
                    except json.JSONDecodeError:
                        continue

            yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Chat failed: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'chunk': f'Error: {str(e)}', 'done': True, 'error': True})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "llm_url": Config.LLAMA_CPP_URL}


if __name__ == "__main__":
    import uvicorn
    host, port = Config.get_server_config()
    uvicorn.run("backend:app", host=host, port=port, reload=True, reload_dirs=[".", "src", "frontend"])
