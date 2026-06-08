import json
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings


def _redis_channel(user_id: str) -> str:
    return f"user:{user_id}:notifications"


async def create_and_publish(
    user_id: str,
    type: str,
    title: str,
    message: str,
    data: Optional[dict] = None,
) -> str:
    from app.core.session import SessionLocal
    from app.modules.notifications import db_service as notif_db

    with SessionLocal() as db:
        notification = notif_db.create_notification(
            db=db,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            data=data,
        )
        payload = json.dumps({
            "id": notification.id,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "data": notification.data,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        })

    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.publish(_redis_channel(user_id), payload)
        await r.aclose()
    except Exception as e:
        print(f"[notifications] Redis publish failed (notification still saved): {e}")

    return notification.id
