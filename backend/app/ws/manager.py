from __future__ import annotations

from typing import Optional

import asyncio
import json
from datetime import datetime, timezone

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from backend.app.core.config import settings

logger = structlog.get_logger()

EVENT_TYPES = [
    "agent.status",
    "task.progress",
    "paper.created",
    "review.completed",
    "token.usage",
    "budget.alert",
    "notification",
]


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self._redis = None
        self._pubsub_task: asyncio.Optional[Task] = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(settings.REDIS_URL)
        return self._redis

    async def start_pubsub(self):
        try:
            r = await self._get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe("ws:broadcast")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    await self._broadcast_raw(data)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.warning("pubsub_listener_error")

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info("ws_connected", user_id=user_id, total=len(self.active_connections))

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        logger.info("ws_disconnected", user_id=user_id, total=len(self.active_connections))

    async def send_personal_message(self, user_id: str, event_type: str, payload: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            message = {
                "type": event_type,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, event_type: str, payload: dict):
        message = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        raw = json.dumps(message)

        try:
            r = await self._get_redis()
            await r.publish("ws:broadcast", raw)
        except Exception:
            await self._broadcast_raw(raw)

    async def _broadcast_raw(self, raw_message: str):
        disconnected = []
        for user_id, ws in self.active_connections.items():
            try:
                await ws.send_text(raw_message)
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            self.disconnect(uid)

    async def shutdown(self):
        if self._redis:
            await self._redis.aclose()
        for user_id in list(self.active_connections.keys()):
            ws = self.active_connections.get(user_id)
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass
        self.active_connections.clear()


ws_manager = ConnectionManager()
