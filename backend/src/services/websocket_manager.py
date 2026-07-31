import logging

from fastapi import WebSocket

from schemas.metrics import StatusDeltaMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket Connection Manager for Live Status Delta Broadcasting.
    - Manages active client connections.
    - Broadcasts lightweight status delta messages to all authenticated clients.
    - Resilient to unexpected disconnects and client drops.
    """

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast_status_delta(self, delta: StatusDeltaMessage) -> None:
        """
        Broadcast status delta to all connected clients.
        """
        payload = delta.model_dump()
        disconnected: list[WebSocket] = []

        for connection in self.active_connections:
            try:
                await connection.send_json(payload)
            except Exception as exc:
                logger.warning(f"Error sending WebSocket message to client: {exc}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


status_ws_manager = ConnectionManager()
