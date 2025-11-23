"""Pydantic models for API requests and responses."""
from pydantic import BaseModel
from typing import List, Dict, Optional


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    conversation_history: List[Dict[str, str]] = []
    session_id: Optional[str] = None
    model_provider: Optional[str] = None  # 'llamacpp', 'gemini', or 'openai'
    response_style: Optional[str] = "Normal"  # 'Normal', 'Formal', 'Explanatory', 'Concise', 'Learning'


class SessionCreate(BaseModel):
    """Session creation request."""
    title: str


class SessionUpdate(BaseModel):
    """Session update request."""
    title: str


class MessageCreate(BaseModel):
    """Message creation request."""
    session_id: str
    role: str
    content: str
