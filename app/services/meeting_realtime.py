import asyncio
from collections import defaultdict

from fastapi import WebSocket


class MeetingConnectionManager:
    """In-memory signaling for a single API process. Use a shared broker for multi-worker deployments."""

    def __init__(self):
        self._connections: dict[tuple[str, int], dict[int, set[WebSocket]]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def join(self, tenant_id: str, meeting_id: int, user_id: int, websocket: WebSocket) -> list[int]:
        key = (tenant_id, meeting_id)
        async with self._lock:
            participants = self._connections[key]
            existing_ids = list(participants.keys())
            participants.setdefault(user_id, set()).add(websocket)
            return existing_ids

    async def leave(self, tenant_id: str, meeting_id: int, user_id: int, websocket: WebSocket) -> list[int]:
        key = (tenant_id, meeting_id)
        async with self._lock:
            participants = self._connections.get(key, {})
            sockets = participants.get(user_id, set())
            sockets.discard(websocket)
            if not sockets:
                participants.pop(user_id, None)
            if not participants:
                self._connections.pop(key, None)
            return list(participants.keys())

    async def send_to_user(self, tenant_id: str, meeting_id: int, user_id: int, payload: dict) -> bool:
        async with self._lock:
            sockets = list(self._connections.get((tenant_id, meeting_id), {}).get(user_id, set()))
        if not sockets:
            return False
        results = await asyncio.gather(*(socket.send_json(payload) for socket in sockets), return_exceptions=True)
        return any(not isinstance(result, Exception) for result in results)

    async def broadcast(self, tenant_id: str, meeting_id: int, payload: dict, exclude_user_id: int | None = None) -> None:
        async with self._lock:
            sockets = [
                socket
                for user_id, user_sockets in self._connections.get((tenant_id, meeting_id), {}).items()
                if user_id != exclude_user_id
                for socket in user_sockets
            ]
        if sockets:
            await asyncio.gather(*(socket.send_json(payload) for socket in sockets), return_exceptions=True)


meeting_connections = MeetingConnectionManager()
