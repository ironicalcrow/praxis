import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.core.supabase import supabase
from app.modules.auth.dependency import get_current_user
from app.modules.notifications import db_service as notif_db
from app.modules.notifications.schemas import NotificationOut
from app.modules.notifications.ws_manager import manager

router = APIRouter()


# ── REST ───────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return notif_db.get_notifications(db, str(current_user.id), unread_only=unread_only)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    n = notif_db.mark_read(db, str(notification_id), str(current_user.id))
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n


@router.post("/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = notif_db.mark_all_read(db, str(current_user.id))
    return {"marked_read": count}


@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deleted = notif_db.delete_notification(db, str(notification_id), str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")


# ── WebSocket ──────────────────────────────────────────────────────────────────

async def ws_notifications(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        response = supabase.auth.get_user(token)
        user = response.user
        if not user:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4001, reason="Auth failed")
        return

    user_id = str(user.id)

    await manager.connect(user_id, websocket)

    # Push all unread notifications immediately on connect
    from app.core.session import SessionLocal
    with SessionLocal() as db:
        unread = notif_db.get_notifications(db, user_id, unread_only=True)
        for n in unread:
            try:
                await websocket.send_text(json.dumps({
                    "id": n.id,
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "data": n.data,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat(),
                }))
            except Exception:
                break

    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user_id, websocket)
