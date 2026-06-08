import asyncio
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.modules.notifications.service import create_and_publish as notify

from app.core.session import get_db
from app.modules.auth.dependency import get_current_user
from app.modules.chat import db_service as chat_db
from app.modules.chat import service as chat_service
from app.modules.chat.schemas import (
    ConversationCreate,
    ConversationOut,
    SessionCreate,
    SessionOut,
    SessionSummaryOut,
    ChatMessageIn,
    ChatMessageOut,
    ChatResponse,
    SimpleMessageIn,
    SimpleMessageOut,
)

router = APIRouter()


# ── Zero-friction endpoints (user-facing) ─────────────────────────────────────

@router.post("/message", response_model=SimpleMessageOut)
async def send_simple_message(
    body: SimpleMessageIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """General coaching chat — auto-manages conversation and session lifecycle."""
    try:
        result = await chat_service.send_message(
            content=body.content,
            user_id=str(current_user.id),
            db=db,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/job/{job_id}/message", response_model=SimpleMessageOut)
async def send_job_message(
    job_id: UUID,
    body: SimpleMessageIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Job-scoped coaching chat — conversation is tied to this specific job."""
    try:
        result = await chat_service.send_message(
            content=body.content,
            user_id=str(current_user.id),
            db=db,
            job_id=str(job_id),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/history", response_model=list[ChatMessageOut])
def get_chat_history(
    limit: int = Query(default=20, le=50),
    before: Optional[str] = Query(default=None, description="Message ID for cursor pagination"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Paginated message history for the general coaching chat (newest first)."""
    conv = chat_db.get_or_create_general_conversation(db, str(current_user.id))
    return chat_db.get_recent_messages(db, conv.id, limit=limit, before_id=before)


@router.get("/job/{job_id}/history", response_model=list[ChatMessageOut])
def get_job_chat_history(
    job_id: UUID,
    limit: int = Query(default=20, le=50),
    before: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Paginated message history for a job-specific chat."""
    conv = chat_db.get_or_create_job_conversation(db, str(current_user.id), str(job_id))
    return chat_db.get_recent_messages(db, conv.id, limit=limit, before_id=before)


@router.get("/sessions", response_model=list[SessionSummaryOut])
def get_session_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List of past sessions with summaries — powers the history cards UI."""
    conv = chat_db.get_or_create_general_conversation(db, str(current_user.id))
    return chat_db.get_session_summaries(db, conv.id)


@router.get("/job/{job_id}/sessions", response_model=list[SessionSummaryOut])
def get_job_session_history(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List of past sessions for a job-specific chat."""
    conv = chat_db.get_or_create_job_conversation(db, str(current_user.id), str(job_id))
    return chat_db.get_session_summaries(db, conv.id)


# ── Conversations (legacy — kept for backward compatibility) ───────────────────

@router.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return chat_db.create_conversation(db, str(current_user.id), body.title)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return chat_db.get_conversations(db, str(current_user.id))


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation_id = str(conversation_id)
    conv = chat_db.get_conversation(db, conversation_id, str(current_user.id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


# ── Sessions ───────────────────────────────────────────────────────────────────

@router.post(
    "/conversations/{conversation_id}/sessions",
    response_model=SessionOut,
    status_code=201,
)
def create_session(
    conversation_id: UUID,
    body: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation_id = str(conversation_id)
    conv = chat_db.get_conversation(db, conversation_id, str(current_user.id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return chat_db.create_session(db, conversation_id, body.title)


@router.get(
    "/conversations/{conversation_id}/sessions",
    response_model=list[SessionOut],
)
def list_sessions(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation_id = str(conversation_id)
    conv = chat_db.get_conversation(db, conversation_id, str(current_user.id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return chat_db.get_sessions(db, conversation_id)


# ── Messages ───────────────────────────────────────────────────────────────────

@router.get(
    "/conversations/{conversation_id}/sessions/{session_id}/messages",
    response_model=list[ChatMessageOut],
)
def get_messages(
    conversation_id: UUID,
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation_id = str(conversation_id)
    session_id = str(session_id)
    conv = chat_db.get_conversation(db, conversation_id, str(current_user.id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return chat_db.get_session_messages(db, session_id)


@router.post(
    "/conversations/{conversation_id}/sessions/{session_id}/message",
    response_model=ChatResponse,
)
async def send_message(
    conversation_id: UUID,
    session_id: UUID,
    body: ChatMessageIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation_id = str(conversation_id)
    session_id = str(session_id)

    conv = chat_db.get_conversation(db, conversation_id, str(current_user.id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    session = chat_db.get_session(db, session_id)
    if not session or session.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = await chat_service.generate_chat_response(
            user_message=body.content,
            session_id=session_id,
            conversation_id=conversation_id,
            user_id=str(current_user.id),
            db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

    return result


# ── Summarize ──────────────────────────────────────────────────────────────────

@router.post("/conversations/{conversation_id}/summarize")
async def summarize_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation_id = str(conversation_id)
    conv = chat_db.get_conversation(db, conversation_id, str(current_user.id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        summary = await chat_service.generate_conversation_summary(conversation_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

    asyncio.create_task(notify(
        user_id=str(current_user.id),
        type="conversation_summarized",
        title="Coaching session saved",
        message=f"Key insights from \"{conv.title}\" have been saved as memory for future sessions.",
        data={"conversation_id": conversation_id},
    ))
    return {"conversation_id": conversation_id, "summary": summary}
