# routers/agent_decisor.py
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
from typing import Any, Dict, Optional
import asyncio
import logging
from pydantic import ValidationError

from app.models import AgentRequest, AgentResponse, ToolCallContext, DecisionPackageMCP
from app.deps import require_mcp_access

router = APIRouter()
logger = logging.getLogger("router.decisor")


# Dependency to fetch the singleton decisor agent from app.state
def get_decisor_agent(request: Request):
    agents = getattr(request.app.state, "agents", None)
    if not agents or "decisor" not in agents:
        raise HTTPException(status_code=503, detail="Decisor agent not available")
    return agents["decisor"]


# ---------------------------
# MCP-compatible POST endpoint
# ---------------------------
@router.post(
    "/run",
    response_model=AgentResponse,
    summary="Invoke Decisor Agent (FastMCP/LibreChat)",
    description="Consumes an AgentRequest and returns an AgentResponse consumable by FastMCP or LibreChat.",
)
async def run_decisor_mcp(
    request_data: AgentRequest,
    agent=Depends(get_decisor_agent),
    token: Optional[str] = Depends(require_mcp_access),
) -> AgentResponse:
    """
    Executes the Decisor agent using either async 'ainvoke' if available, 
    or fallback to threadpool execution to avoid blocking.
    
    Input:
    - instruction (str): Prompt for the Decisor agent.
    - tool_context (ToolCallContext, optional): Metadata from MCP client.

    Output:
    - AgentResponse: Contains the agent output, finished flag, and optional debug info.
    """
    instruction: str = request_data.instruction
    tool_ctx: Optional[ToolCallContext] = request_data.tool_context

    logger.info("Received MCP decisor request: %s", instruction)
    if tool_ctx:
        logger.debug("Tool context: %s", tool_ctx.dict())

    try:
        # Ejecutar el agente (async si disponible, fallback a threadpool)
        if hasattr(agent, "ainvoke"):
            logger.debug("Using agent.ainvoke() for async execution")
            result = await asyncio.wait_for(agent.ainvoke({"input": instruction}), timeout=60)
            raw_output = result.get("output") if isinstance(result, dict) else str(result)
        else:
            logger.debug("Using run_in_threadpool(agent.run)")
            res = await run_in_threadpool(agent.run, instruction)
            raw_output = str(res)

        # ---------------------------
        # Parseo y validación como DecisionPackageMCP
        # ---------------------------
        try:
            parsed_dict = json.loads(raw_output)
            validated_package = DecisionPackageMCP.model_validate(parsed_dict)  # Pydantic v2
            validated_json = validated_package.model_dump_json()  # JSON validado
        except (json.JSONDecodeError, ValidationError) as e:
            logger.exception("Failed to parse/validate DecisionPackageMCP: %s", e)
            return AgentResponse(
                output=f"Error: Agent failed to produce valid DecisionPackage structured output.",
                finished=True,
                debug={
                    "raw_output": raw_output,
                    "error": str(e),
                    "tool_context": tool_ctx.dict() if tool_ctx else None,
                },
            )

    except Exception as exc:
        logger.exception("Decisor agent invocation failed: %s", exc)
        return AgentResponse(
            output=f"Error executing decisor agent: {exc}",
            finished=True,
            debug={"exception": str(exc)},
        )

    return AgentResponse(
        output=validated_json,
        finished=True,
        debug={
            "tool_context": tool_ctx.dict() if tool_ctx else None,
            "instruction": instruction,
        },
    )