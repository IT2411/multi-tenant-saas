import asyncio
import json
import uuid
from typing import Any

import redis.asyncio as aioredis
import structlog
from fastapi import WebSocket

from app.core.config import settings
from app.core.redis import redis_client

logger = structlog.get_logger(__name__)


class WebSocketHub:
    """Manages active project room WebSocket connections and Redis Pub/Sub cross-instance broadcasting."""

    def __init__(self) -> None:
        self.rooms: dict[uuid.UUID, set[WebSocket]] = {}
        self._listener_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}
        self._sub_client: aioredis.Redis | None = None

    def _channel_name(self, project_id: uuid.UUID) -> str:
        return f"project_events:{project_id}"

    def _get_sub_client(self) -> aioredis.Redis:
        if self._sub_client is None:
            self._sub_client = aioredis.from_url(  # type: ignore[no-untyped-call]
                str(settings.REDIS_URI),
                encoding="utf-8",
                decode_responses=True,
            )
        return self._sub_client

    async def connect(self, project_id: uuid.UUID, websocket: WebSocket) -> None:
        """Accepts WebSocket and subscribes to project room."""
        await websocket.accept()
        if project_id not in self.rooms:
            self.rooms[project_id] = set()
            task = asyncio.create_task(self._listen_redis_channel(project_id))
            self._listener_tasks[project_id] = task

        self.rooms[project_id].add(websocket)
        logger.info(
            "ws_client_connected",
            project_id=str(project_id),
            total_room_clients=len(self.rooms[project_id]),
        )

    async def disconnect(self, project_id: uuid.UUID, websocket: WebSocket) -> None:
        """Removes WebSocket and tears down Redis listener if room is empty."""
        if project_id in self.rooms:
            self.rooms[project_id].discard(websocket)
            if not self.rooms[project_id]:
                del self.rooms[project_id]
                if project_id in self._listener_tasks:
                    self._listener_tasks[project_id].cancel()
                    del self._listener_tasks[project_id]

        logger.info("ws_client_disconnected", project_id=str(project_id))

    async def broadcast_to_room(self, project_id: uuid.UUID, event_type: str, data: Any) -> None:
        """Publishes an event to Redis Pub/Sub for distribution across all application instances."""
        channel = self._channel_name(project_id)
        payload = json.dumps({"event": event_type, "data": data})
        try:
            await redis_client.publish(channel, payload)
        except Exception as exc:
            logger.warning("ws_broadcast_failed", channel=channel, error=str(exc))

    async def _listen_redis_channel(self, project_id: uuid.UUID) -> None:
        """Background listener reading messages from Redis and distributing to local room sockets."""
        sub_client = self._get_sub_client()
        pubsub = sub_client.pubsub()
        channel = self._channel_name(project_id)
        await pubsub.subscribe(channel)

        try:
            while project_id in self.rooms:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("data"):
                    raw_data: str = message["data"]
                    dead_sockets: list[WebSocket] = []

                    for ws in list(self.rooms.get(project_id, set())):
                        try:
                            await ws.send_text(raw_data)
                        except Exception:
                            dead_sockets.append(ws)

                    for ws in dead_sockets:
                        await self.disconnect(project_id, ws)

                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)


ws_hub = WebSocketHub()
