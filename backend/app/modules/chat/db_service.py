from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import delete

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


# ── Zero-friction helpers (used by simplified endpoints) ──────────────────────

def get_or_create_general_conversation(db: Session, user_id: str) -> ChatConversation:
    """Find the user's single general coaching conversation, creating it if missing."""
    conv = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.user_id == user_id,
            ChatConversation.context_type == "general",
        )
        .first()
    )
    if not conv:
        conv = ChatConversation(user_id=user_id, title="Career Coaching", context_type="general")
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return conv


def get_or_create_job_conversation(db: Session, user_id: str, job_id: str) -> ChatConversation:
    """Find or create one job-scoped conversation per (user, job) pair."""
    conv = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.user_id == user_id,
            ChatConversation.context_type == "job",
            ChatConversation.job_id == job_id,
        )
        .first()
    )
    if not conv:
        from app.modules.jobs.models import Job
        job = db.query(Job).filter(Job.id == job_id).first()
        title = f"{job.title} @ {job.company_name}" if job else "Job Discussion"
        conv = ChatConversation(
            user_id=user_id, title=title, context_type="job", job_id=job_id
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return conv


def get_or_create_active_session(db: Session, conversation_id: str) -> ChatSession:
    """
    Return the active session for this conversation.
    If none exists, or message_count >= 15, rotate: mark old inactive, create new one.
    Actual summarization is triggered separately as a background task.
    """
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.conversation_id == conversation_id,
            ChatSession.is_active == True,
        )
        .first()
    )
    if session and session.message_count < 15:
        return session

    if session:
        session.is_active = False
        db.commit()

    new_session = ChatSession(conversation_id=conversation_id, is_active=True, message_count=0)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def increment_message_count(db: Session, session_id: str) -> int:
    """Increment message_count and return new value."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        session.message_count = (session.message_count or 0) + 1
        db.commit()
        return session.message_count
    return 0


def save_session_summary(db: Session, session_id: str, summary: str) -> None:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        session.session_summary = summary
        db.commit()


def get_session_summaries(db: Session, conversation_id: str) -> list[ChatSession]:
    """All sessions for a conversation ordered newest-first — used for history cards."""
    return (
        db.query(ChatSession)
        .filter(ChatSession.conversation_id == conversation_id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )


def get_recent_messages(
    db: Session, conversation_id: str, limit: int = 20, before_id: Optional[str] = None
) -> list[ChatMessage]:
    """
    Paginated message history across the active session.
    Returns messages newest-first for cursor pagination.
    """
    active_session = (
        db.query(ChatSession)
        .filter(
            ChatSession.conversation_id == conversation_id,
            ChatSession.is_active == True,
        )
        .first()
    )
    if not active_session:
        return []

    q = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == active_session.id)
    )
    if before_id:
        pivot = db.query(ChatMessage).filter(ChatMessage.id == before_id).first()
        if pivot:
            q = q.filter(ChatMessage.created_at < pivot.created_at)

    return q.order_by(ChatMessage.created_at.desc()).limit(limit).all()


def prune_old_messages(db: Session, conversation_id: str, keep_sessions: int = 2) -> int:
    """
    Delete raw messages from completed sessions beyond the most recent `keep_sessions`.
    Session rows and summaries are never deleted.
    Returns number of messages deleted.
    """
    completed = (
        db.query(ChatSession)
        .filter(
            ChatSession.conversation_id == conversation_id,
            ChatSession.is_active == False,
        )
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    to_prune = completed[keep_sessions:]
    if not to_prune:
        return 0

    prune_ids = [s.id for s in to_prune]
    result = db.execute(
        delete(ChatMessage).where(ChatMessage.session_id.in_(prune_ids))
    )
    db.commit()
    return result.rowcount
