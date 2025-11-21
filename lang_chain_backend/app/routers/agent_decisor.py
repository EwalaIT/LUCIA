# routers/agent_decisor.py
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
from typing import Any
import asyncio
import logging

from app.models import DecisorRequest, AgentResponse

router = APIRouter()
logger = logging.getLogger("router.decisor")


# Dependency to fetch the singleton decisor agent from app.state
def get_decisor_agent(request: Request):
    agents = getattr(request.app.state, "agents", None)
    if not agents or "decisor" not in agents:
        raise HTTPException(status_code=503, detail="Decisor agent not available")
    return agents["decisor"]


@router.post("/run", response_model=AgentResponse)
async def run_decisor(request_data: DecisorRequest, agent=Depends(get_decisor_agent)) -> AgentResponse:
    """
    Run the decisor agent on the provided instruction.
    Uses async invocation if available; otherwise runs in threadpool to avoid blocking.
    """
    instruction = request_data.instruction
    logger.info("Received decisor request: %s", instruction)

    try:
        # Prefer async API exposed by AgentExecutor (if present)
        if hasattr(agent, "ainvoke"):
            logger.debug("Using agent.ainvoke() for async invocation")
            result = await asyncio.wait_for(agent.ainvoke({"input": instruction}), timeout=60)
            # many agent invoke methods return dict-like with 'output' or plain str
            output = result.get("output") if isinstance(result, dict) else str(result)
        else:
            # Fallback to running blocking call in threadpool
            logger.debug("Using run_in_threadpool(agent.run)")
            res = await run_in_threadpool(agent.run, instruction)
            output = str(res)
    except Exception as exc:
        logger.exception("Decisor agent invocation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return AgentResponse(output=output)
