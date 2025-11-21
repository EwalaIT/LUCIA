# routers/agent_db_query.py
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
import asyncio
import logging

from app.models import QueryRequest, AgentResponse

router = APIRouter()
logger = logging.getLogger("router.dbquery")

try:
    from langchain_core.language_models import BaseLanguageModel
except ImportError:
    BaseLanguageModel = object


def get_db_query_agent(request: Request):
    agents = getattr(request.app.state, "agents", None)
    if not agents or "db_query" not in agents:
        raise HTTPException(status_code=503, detail="DB Query agent not available")
    return agents["db_query"]


@router.post("/query", response_model=AgentResponse)
async def run_db_query(request_data: QueryRequest, agent=Depends(get_db_query_agent)) -> AgentResponse:
    question = request_data.question
    logger.info("Received DB query request: %s", question)

    try:
        if hasattr(agent, "ainvoke"):
            logger.debug("Using agent.ainvoke() for async invocation")
            result = await asyncio.wait_for(agent.ainvoke({"input": question}), timeout=60)
            output = result.get("output") if isinstance(result, dict) else str(result)
        else:
            res = await run_in_threadpool(agent.run, question)
            output = str(res)
    except Exception as exc:
        logger.exception("DB Query agent invocation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return AgentResponse(output=output)
