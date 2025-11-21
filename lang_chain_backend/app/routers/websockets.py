import json
import logging
from asyncio import Lock
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()
connections_lock = Lock()
active_connections: List[WebSocket] = []


@router.websocket("/ws/decisions")
async def decisions_websocket(websocket: WebSocket):
    """Canal WebSocket para notificar cambios en decisiones."""
    await websocket.accept()
    async with connections_lock:
        active_connections.append(websocket)
    logger.info(f"🟢 WebSocket connected: {len(active_connections)} clients")

    try:
        while True:
            await websocket.receive_text()  # mantener viva la conexión
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"🔴 WebSocket disconnected. {len(active_connections)} clients remaining.")

async def broadcast_decision_update(decision_id: int, status: str):
    """Envía una notificación de cambio de estado a todos los clientes conectados."""
    message = json.dumps({"decision_id": decision_id, "status": status})
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    # Limpiar conexiones muertas
    for ws in disconnected:
        active_connections.remove(ws)
    logger.info(f"📢 Broadcast decision {decision_id} -> {status} to {len(active_connections)} clients")