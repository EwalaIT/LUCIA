# services/agent_decisor.py
import logging
import asyncio
import json
from typing import Optional, Any, Dict

from config import settings
from langchain_core.language_models import BaseLanguageModel
from langchain_ollama import ChatOllama
from langchain.agents import create_agent

# Tools (HA, VLM, Safety)
from services.ha_tools import (
    get_current_state_tool,
    call_service_tool,
    safety_check_tool,
    vlm_fetch_tool,
)

# DB tool (insert decision)
from db.decisions import validate_decision_package, persist_new_decision

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _build_prompt() -> str:
    """
    Returns the system message content for the Energy Efficiency Decisor Agent.
    This establishes the role, reasoning process, required JSON format, and mandatory safety protocol.
    """
    return (
        "You are an expert Energy Efficiency and Device Control Agent. Your primary function is to optimize resource consumption based on natural language instructions, context, and environment variables.\n"
        "**Protocol:** You must use rigorous, step-by-step internal reasoning and ONLY utilize the available tools (Device State Retrieval, Service Execution, or Vision/VLM). Do not perform calculations or estimations without using a tool if a tool is provided for that purpose.\n"
        "**Required Output Format:** You MUST return a single, valid JSON object named 'DecisionPackage' with the following fields:\n"
        " - **chain_of_thought (string):** A detailed, professional explanation of your logic, state interpretation, and decision path.\n"
        " - **suggested_actions (list of objects):** A list of final action objects, each containing {action, target_entity, parameters, rationale}.\n"
        "**Mandatory Safety Chain:**\n"
        "1. **Safety Check:** Before concluding and executing any real action, you MUST call the 'safety_check' tool, passing the entire DecisionPackage JSON (your intended output) as input.\n"
        "2. **Decision Logging:** If the 'safety_check' confirms the actions are safe, you MUST call the 'insert_decision' tool to log the DecisionPackage.\n"
        "Your final response to the user query MUST be the complete, valid DecisionPackage JSON object."
    )


def create_decisor_agent(llm: BaseLanguageModel):
    """
    Crea y devuelve un agente decisor basado en LangChain v1.x.
    Usa el método canónico create_agent, que devuelve un Runnable.
    """
    system_prompt = _build_prompt()

    tools = [
        get_current_state_tool,
        call_service_tool,
        vlm_fetch_tool,
        safety_check_tool,
    ]

    try:
        llm = ChatOllama(
            base_url=str(settings.ollama_url),
            model=settings.ollama_model,
        )
        agent = create_agent(
            llm,
            tools=tools,
            system_prompt=system_prompt,
        )
        logger.info("✅ Decisor Agent creado correctamente con create_agent().")
        return agent
    except Exception as e:
        logger.exception("❌ Error al crear el Decisor Agent: %s", e)
        raise


def _extract_json_from_text(raw: str) -> dict:
    """
    Attempts to find a JSON object inside raw text. Uses a simple but robust strategy:
    - finds the first '{' and the matching closing '}' by scanning (handles nested braces).
    Raises ValueError on failure.
    """
    json_candidates = re.findall(r'\{.*\}', raw, flags=re.DOTALL)
    for candidate in json_candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No JSON object could be extracted from agent output: {raw[:200]}")


async def run_decisor(app, ha_instance: str, context: dict, reason: str = "observation") -> Optional[Dict[str, Any]]:
    """
    Asynchronously run the Decisor agent, persist the produced decision, and return a dict:
    { "decision_id": int, "decision_package": dict }
    """
    agent = getattr(app.state, "agents", {}).get("decisor")
    if not agent:
        logger.error("Decisor agent not available in app.state.agents")
        return None

    # Build agent input
    input_text = (
        f"Trigger reason: {reason}\n"
        f"HA instance: {ha_instance}\n"
        f"Context snapshot: {json.dumps(context, ensure_ascii=False)}\n"
        "Produce a DecisionPackage JSON as specified."
    )

    # Invoke the agent in thread to avoid blocking
    try:
        result = await asyncio.to_thread(lambda: agent.invoke({"input": input_text}))
    except Exception as e:
        logger.exception("Error invoking decisor agent: %s", e)
        return None

    # Normalize result -> raw text
    raw = ""
    try:
        if isinstance(result, dict):
            # Various langchain versions might return 'output' or 'messages'
            if "output" in result:
                raw = result["output"]
            elif "messages" in result:
                msgs = result["messages"]
                raw = getattr(msgs[-1], "content", str(msgs[-1]))
            else:
                raw = str(result)
        else:
            raw = str(result)
    except Exception:
        raw = str(result)

    # Try to extract JSON from raw text
    try:
        dp = _extract_json_from_text(raw)
    except Exception as e:
        logger.exception("Failed to extract DecisionPackage JSON from agent output: %s", e)
        # persist a raw fallback decision so operator can inspect
        raw_pkg = {"raw_output": raw}
        dp_json_str = json.dumps(raw_pkg, ensure_ascii=False)
        decision_id = persist_new_decision(
            decision_package_json=dp_json_str,
            agent_name="decisor",
            goal=None,
            reasoning="failed_parse",
            confidence=None,
            context_id=None,
            status="PENDING",
        )
        return {"decision_id": decision_id, "decision_package": raw_pkg}

    # Validate structure
    try:
        validate_decision_package(dp)
    except Exception as e:
        logger.warning("DecisionPackage validation failed: %s. We will still persist for manual inspection.", e)
        # We persist even invalid DP for audit purposes, but include validation info.
        dp["_validation_error"] = str(e)

    # Persist decision
    try:
        dp_json_str = json.dumps(dp, ensure_ascii=False)
        decision_id = persist_new_decision(
            decision_package_json=dp_json_str,
            agent_name="decisor",
            goal=dp.get("goal"),
            reasoning=dp.get("chain_of_thought"),
            confidence=dp.get("confidence"),
            context_id=None,
            status="PENDING",
            decision_type=dp.get("decision_type"),
            zone_id=dp.get("zone_id"),
        )
        logger.info("Decisor produced decision id=%s", decision_id)
    except Exception as e:
        logger.exception("Failed to persist decision: %s", e)
        return None

    return {"decision_id": decision_id, "decision_package": dp}