import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from core.security import decode_access_token
from services.websocket_manager import status_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def authenticate_websocket(websocket: WebSocket, token: str | None) -> dict | None:
    """
    Authenticate WebSocket connection using query parameter token.
    Returns decoded JWT payload if valid, None otherwise.
    """
    if not token:
        return None
    payload = decode_access_token(token)
    return payload


@router.websocket("/ws/status")
@router.websocket("/api/v1/ws/status")
async def websocket_status_delta_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT Access Token"),
):
    payload = await authenticate_websocket(websocket, token)
    if not payload:
        logger.warning("Rejected unauthenticated WebSocket status connection attempt.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized token")
        return

    await status_ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open, listen for client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        status_ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(f"WebSocket client error: {exc}")
        status_ws_manager.disconnect(websocket)
