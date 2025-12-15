# app/routers/execution.py
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request, HTTPException

from services.decision_executor import async_execute_decision
from services.ha_tools import HomeAssistantAPI
from db.decisions import get_decision_by_id, update_decision_status
from app.routers.websockets import broadcast_decision_update

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{decision_id}/execute")
async def execute_decision_endpoint(decision_id: int, request: Request):
    app = request.app
    # Verify decision exists
    row = await asyncio.to_thread(get_decision_by_id, decision_id)
    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Use app.state.httpx_client? We use HomeAssistantAPI that uses requests (sync)
    ha_api = HomeAssistantAPI()

    # Execute asynchronously
    try:
        llm = request.app.state.agents.get("llm")
        result = await async_execute_decision(decision_id, app.state.db_path, ha_api, llm=llm)
    except Exception as e:
        logger.exception("Decision execution failed")
        raise HTTPException(status_code=500, detail=str(e))

    # Broadcast result to connected WebSocket clients
    try:
        await broadcast_decision_update(decision_id, result.get("status", "UNKNOWN"))
    except Exception:
        logger.exception("Failed to broadcast decision update via websockets")

    return {"decision_id": decision_id, "status": result.get("status"), "details": result.get("actions")}


@router.post("/{decision_id}/reject")
async def reject_decision_endpoint(decision_id: int):
    # mark as rejected
    await asyncio.to_thread(update_decision_status, decision_id, "REJECTED", summary="Manually rejected via API")
    # broadcast
    try:
        await broadcast_decision_update(decision_id, "REJECTED")
    except Exception:
        logger.exception("Failed to broadcast REJECTED")
    return {"decision_id": decision_id, "status": "REJECTED"}