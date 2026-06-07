from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


# ── Conversation ───────────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str


class ConversationOut(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Session ────────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionOut(BaseModel):
    id: str
    conversation_id: str
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Message ────────────────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    content: str


class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Structured AI Response ─────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """
    Returned after a user sends a message.
    raw_content is the full markdown text from the LLM.
    """
    message: ChatMessageOut
    raw_content: str
    session_id: str
    conversation_id: str
