import asyncio
import json
from typing import Optional

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import settings


class NotificationManager:
    def __init__(self):
        # user_id -> list of (websocket, listener_task) tuples
        self._connections: dict[str, list[tuple[WebSocket, asyncio.Task]]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        task = asyncio.create_task(self._redis_listener(user_id, websocket))
        self._connections.setdefault(user_id, []).append((websocket, task))

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(user_id, [])
        for i, (ws, task) in enumerate(conns):
            if ws is websocket:
                task.cancel()
                conns.pop(i)
                break
        if not conns:
            self._connections.pop(user_id, None)

    async def _redis_listener(self, user_id: str, websocket: WebSocket) -> None:
        channel = f"user:{user_id}:notifications"
        r: Optional[aioredis.Redis] = None
        pubsub = None
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)

            async for raw_message in pubsub.listen():
                if raw_message["type"] != "message":
                    continue
                try:
                    await websocket.send_text(raw_message["data"])
                except Exception:
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ws_manager] Redis listener error for {user_id}: {e}")
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.aclose()
                except Exception:
                    pass
            if r:
                try:
                    await r.aclose()
                except Exception:
                    pass


manager = NotificationManager()
