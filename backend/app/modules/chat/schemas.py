from datetime import datetime
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel


# ── Conversation ───────────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str


class ConversationOut(BaseModel):
    id: str
    title: str
    context_type: str = "general"
    job_id: Optional[str] = None
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


class SessionSummaryOut(BaseModel):
    """Collapsed history card shown in the UI for past sessions."""
    id: str
    conversation_id: str
    session_summary: Optional[str] = None
    message_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Message ────────────────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    content: str


class SimpleMessageIn(BaseModel):
    """Used by the simplified /chat/message and /chat/job/{job_id}/message endpoints."""
    content: str


class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatToolStatus(str, Enum):
    handled = "handled"
    unsupported = "unsupported"
    failed = "failed"
    confirmation_required = "confirmation_required"


class ChatUIPayload(BaseModel):
    type: str
    data: Any | None = None


class ChatNotificationPayload(BaseModel):
    created: bool = False
    notification_id: str | None = None


class SimpleMessageOut(BaseModel):
    """Returned by the simplified send-message endpoints."""
    content: str
    session_id: str
    conversation_id: str
    created_at: datetime
    tool_status: ChatToolStatus = ChatToolStatus.handled
    ui_payload: ChatUIPayload | None = None
    notification: ChatNotificationPayload | None = None


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
