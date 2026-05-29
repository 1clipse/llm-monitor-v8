import json
from fastapi import WebSocket

from app.metrics import ACTIVE_WEBSOCKETS


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        ACTIVE_WEBSOCKETS.set(len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        ACTIVE_WEBSOCKETS.set(len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        stale = []
        payload = json.dumps(message, ensure_ascii=False, default=str)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


manager = ConnectionManager()
