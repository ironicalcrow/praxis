from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from app.core.session import Base
from app.core.utils import generate_uuid


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)

    # "general" | "job" — determines which tools and context are loaded
    context_type = Column(String(20), nullable=False, server_default="general")
    # set when context_type == "job"; one conversation per (user, job) pair
    job_id = Column(String, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)

    summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = relationship(
        "ChatSession",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatSession.created_at",
    )


class ChatSession(Base):
    """One focused chat within a broader conversation topic."""
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String, ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(255), nullable=True)

    # auto-rotation: when message_count hits 15, session is summarized and rotated
    message_count = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")
    # LLM-generated summary of this session — shown as history card in UI
    session_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("ChatConversation", back_populates="sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    """Individual turn (user or assistant) within a session."""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(
        String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(10), nullable=False)   # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
