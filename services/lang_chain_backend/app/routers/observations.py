from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
import logging
import asyncio

from app.models import Observation

router = APIRouter()
logger = logging.getLogger("app.observations")


@router.post("/observations", status_code=status.HTTP_202_ACCEPTED)
async def receive_observation(observation: Observation, request: Request):
    """
    Receives an aggregated Observation (per zone) and pushes it into the app.state.observations_queue.
    Returns 202 Accepted immediately to decouple producer/consumer.
    """
    # Ensure queue exists
    queue: asyncio.Queue[Observation] = getattr(request.app.state, "observations_queue", None)
    if queue is None:
        logger.error("Observations queue not initialized in app.state.")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Observations queue not initialized."},
        )

    # Put the observation in the queue (non-blocking)
    await queue.put(observation)
    logger.debug("🔖 Observation enqueued for async processing.")
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"detail": "Accepted"})