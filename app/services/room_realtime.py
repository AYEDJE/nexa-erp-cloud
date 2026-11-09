import asyncio
from collections import defaultdict

from fastapi import WebSocket


class RoomConnectionManager:
    """Gestion de présence en mémoire, valable pour une instance du backend."""

    def __init__(self):
        self._connections: dict[tuple[str, int], dict[int, set[WebSocket]]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def connect(
        self,
        tenant_id: str,
        room_id: int,
        user_id: int,
        websocket: WebSocket,
    ) -> int:
        key = (tenant_id, room_id)
        async with self._lock:
            user_connections = self._connections[key].setdefault(user_id, set())
            user_connections.add(websocket)
            return len(self._connections[key])

    async def disconnect(
        self,
        tenant_id: str,
        room_id: int,
        user_id: int,
        websocket: WebSocket,
    ) -> int:
        key = (tenant_id, room_id)
        async with self._lock:
            users = self._connections.get(key, {})
            sockets = users.get(user_id, set())
            sockets.discard(websocket)
            if not sockets:
                users.pop(user_id, None)
            if not users:
                self._connections.pop(key, None)
            return len(users)

    async def broadcast(
        self,
        tenant_id: str,
        room_id: int,
        payload: dict,
        exclude: WebSocket | None = None,
    ) -> None:
        key = (tenant_id, room_id)
        async with self._lock:
            sockets = [
                socket
                for user_sockets in self._connections.get(key, {}).values()
                for socket in user_sockets
                if socket is not exclude
            ]

        if sockets:
            await asyncio.gather(
                *(socket.send_json(payload) for socket in sockets),
                return_exceptions=True,
            )

    async def presence(self, tenant_id: str, room_id: int) -> list[int]:
        async with self._lock:
            return list(self._connections.get((tenant_id, room_id), {}).keys())


room_connections = RoomConnectionManager()