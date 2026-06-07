from typing import Optional

from sqlalchemy.orm import Session

from app.modules.chat.models import ChatConversation, ChatSession, ChatMessage


# ── Conversations ──────────────────────────────────────────────────────────────

def create_conversation(db: Session, user_id: str, title: str) -> ChatConversation:
    conv = ChatConversation(user_id=user_id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversations(db: Session, user_id: str) -> list[ChatConversation]:
    return (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user_id)
        .order_by(ChatConversation.updated_at.desc())
        .all()
    )


def get_conversation(
    db: Session, conversation_id: str, user_id: str
) -> Optional[ChatConversation]:
    return (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user_id,
        )
        .first()
    )


def update_conversation_summary(db: Session, conversation_id: str, summary: str):
    conv = (
        db.query(ChatConversation)
        .filter(ChatConversation.id == conversation_id)
        .first()
    )
    if conv:
        conv.summary = summary
        db.commit()


# ── Sessions ───────────────────────────────────────────────────────────────────

def create_session(
    db: Session, conversation_id: str, title: Optional[str] = None
) -> ChatSession:
    session = ChatSession(conversation_id=conversation_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_sessions(db: Session, conversation_id: str) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.conversation_id == conversation_id)
        .order_by(ChatSession.created_at.asc())
        .all()
    )


def get_session(db: Session, session_id: str) -> Optional[ChatSession]:
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()


# ── Messages ───────────────────────────────────────────────────────────────────

def save_message(db: Session, session_id: str, role: str, content: str) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_session_messages(db: Session, session_id: str) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


def get_conversation_all_messages(db: Session, conversation_id: str) -> list[ChatMessage]:
    """All messages across every session in a conversation — used for summary generation."""
    return (
        db.query(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(ChatSession.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


def get_other_sessions_messages(
    db: Session, conversation_id: str, current_session_id: str
) -> list[ChatMessage]:
    """
    All messages in the conversation from sessions OTHER than the current one.
    Injected as prior-session context to maintain thread continuity.
    """
    return (
        db.query(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(
            ChatSession.conversation_id == conversation_id,
            ChatSession.id != current_session_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
