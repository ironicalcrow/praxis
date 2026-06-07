from typing import Optional

from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification


def create_notification(
    db: Session,
    user_id: str,
    type: str,
    title: str,
    message: str,
    data: Optional[dict] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_notifications(
    db: Session, user_id: str, unread_only: bool = False
) -> list[Notification]:
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    return q.order_by(Notification.created_at.desc()).all()


def mark_read(db: Session, notification_id: str, user_id: str) -> Optional[Notification]:
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not n:
        return None
    n.is_read = True
    db.commit()
    db.refresh(n)
    return n


def mark_all_read(db: Session, user_id: str) -> int:
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .update({"is_read": True})
    )
    db.commit()
    return count


def delete_notification(db: Session, notification_id: str, user_id: str) -> bool:
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not n:
        return False
    db.delete(n)
    db.commit()
    return True
