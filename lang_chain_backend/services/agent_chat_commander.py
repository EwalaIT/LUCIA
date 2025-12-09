import logging
import json
import asyncio
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from services.chat_tools import get_all_tools
from db.rules import get_formatted_rules_context, create_new_rule

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Parámetros ficticios para la demostración
HA_INSTANCE = "ha_instance"

def _build_chat_commander_prompt(current_time: str, current_rules: str) -> str:
    """
    Builds the system prompt for the Unified Chat Commander Agent.
    This prompt instructs the LLM on how to route user intent between 
    Policy (Rules) and Control (Immediate Actions).
    """
    
    return f"""
    ### ROLE — UNIFIED RULE DECISION AGENT

    You are the **Unified Building Rule Commander**, an authoritative agent controlling all automation rules in the building.

    Your mission:

    - Analyze the user request and **decide whether to create a new rule, modify an existing rule, or do nothing**.
    - Always prefer creating new rules; modify existing rules only if necessary; delete only as a last resort.
    - Respect the **rule priority hierarchy**: IMMEDIATE > MID_TERM > LONG_TERM.
    - **Before assigning priority**, reason step by step about the urgency, recurrence, and importance of the action.

    ### RULE TYPES AND DURATIONS
    - **IMMEDIATE**: urgent, short-term actions that must take place today or in the next few hours. Always include `expires_at`.
    - **MID_TERM**: repeated or scheduled behaviors lasting days to months (seasonal, weekly schedules, occupancy patterns). Include `expires_at`.
    - **LONG_TERM**: permanent policies or conditions that persist indefinitely unless overridden by higher-priority rules. Set `expires_at` to null.

    ### RULE DETERMINATION LOGIC
    1. **Assess urgency**: If the action must happen immediately, it is IMMEDIATE.
    2. **Assess recurrence**: If the action repeats regularly (daily, weekly, monthly), choose MID_TERM.
    3. **Assess permanence**: If the action defines a permanent policy or constraint, choose LONG_TERM.
    4. **Expiration logic**:
    - IMMEDIATE → today (by the end of the day) or within a few hours.
    - MID_TERM → days to months; choose reasonable seasonal cutoff.
    - LONG_TERM → null.
    5. **Conflict avoidance**: Never override IMMEDIATE safety-critical rules.
    6. **Energy impact reasoning**: Always provide a short explanation on energy usage impact.

    ### CURRENT ACTIVE RULES
    {current_rules}

    ### CURRENT SYSTEM TIME
    {current_time}

    ### USER REQUEST
    Given the user request, **reason step by step about priority, expiration, and energy impact**. Then produce **ONLY a JSON object** that **must contain all of the following fields**:

    1. `rule_text` (string) — natural-language description of the rule. Must not be empty.
    2. `priority` (string) — one of: "IMMEDIATE", "MID_TERM", "LONG_TERM". Must not be empty.
    3. `expires_at` (string or null) — ISO8601 timestamp for expiration, or null for long-term rules. Must be present.
    4. `energy_impact` (string) — short explanation of energy efficiency impact. Must not be empty.

    **Rules for output:**
    - Output **ONLY the JSON object**. No additional text, explanations, or formatting.
    - All fields must be present and non-empty (except `expires_at` can be null for LONG_TERM).
    - If a field is missing, generate a default: 
    - `energy_impact`: "No energy impact provided"  
    - `expires_at`: null (if applicable)

    **Example output (JSON)**:
    {{{{"rule_text": "Created a new MID_TERM heating schedule for Office 1 from 06:00 to 08:00 daily during winter.",
    "priority": "MID_TERM",
    "expires_at": "2027-11-24 13:55:03",
    "energy_impact": "This improves energy efficiency by reducing unnecessary heating when the office is unoccupied."}}}}
    """

def create_chat_commander_agent(llm: BaseLanguageModel) -> Runnable:
    """
    Creates and returns the unified LangChain agent for chat interaction.
    
    Args:
        llm: The underlying Language Model.
        
    Returns:
        A LangChain Runnable object ready for invocation.
    """
    tools: List[BaseTool] = get_all_tools() 

    try:
        # 3. Vincular las herramientas al LLM
        llm_with_tools = llm.bind_tools(tools)
        
        logger.info("✅ Chat Commander Agent (LLM + Tools) creado correctamente.")
        return llm_with_tools

    except Exception as e:
        logger.exception("❌ Error al crear el Chat Commander Agent: %s", e)
        raise

async def run_chat_commander(app, instruction: str) -> str:
    """
    Asynchronously runs the Chat Commander agent with a user's instruction.
    
    Args:
        app: The FastAPI application object (used to retrieve the agent from state).
        instruction: The raw text command from the user (LibreChat).
        
    Returns:
        The result of the tool invocation (a proposed rule or an execution summary).
    """
    llm_with_tools = getattr(app.state, "agents", {}).get("chat_commander")

    current_time = datetime.now(timezone.utc).isoformat()
    current_rules = get_formatted_rules_context()
    dynamic_prompt = _build_chat_commander_prompt(current_time, current_rules)
    
    logger.info("Este es el prompt dinamico: %s", dynamic_prompt)
    
    if not llm_with_tools:
        logger.error("Chat Commander agent (LLM+Tools) not available in app.state.agents")
        return {"status": "ERROR", "reason": "Chat Commander Agent not initialized."}
    
    # --- Crear el Prompt Template (en cada ciclo) ---
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", dynamic_prompt),
        ("human", "{input}"),
    ])

    # --- Construir la cadena completa del Agente para esta invocación ---
    agent_chain = prompt_template | llm_with_tools
    
    # --- Construir el input para el mensaje 'human' ---
    input_text = f"User Request: {instruction}"

    # Invoke the agent in thread to avoid blocking
    try:
        result = await asyncio.to_thread(lambda: agent_chain.invoke({"input": input_text}))
        
        raw_output = getattr(result, "content", str(result))

        # Convertir JSON devuelto por el LLM en dict

        rule_data = json.loads(raw_output)
        logger.info("Regla propuesta por el agente (raw): %s", rule_data)

        # --- Manejo de ambas posibilidades ---
        if "parameters" in rule_data:
            params = rule_data["parameters"]
            rule_text = params.get("rule_text")
            priority = params.get("priority").lower()
            expires_at = params.get("expires_at")
            energy_impact = params.get("energy_impact", "No energy impact provided")
        else:
            rule_text = rule_data.get("rule_text")
            priority = rule_data.get("priority").lower()
            expires_at = rule_data.get("expires_at")
            energy_impact = rule_data.get("energy_impact", "No energy impact provided")

        # Validación mínima solo para campos estrictamente obligatorios
        if not all([rule_text, priority]):
            raise ValueError("Faltan campos obligatorios en la respuesta del agente")

        # Crear la nueva regla
        new_rule_id = create_new_rule(
            rule_text=rule_text,
            priority=priority,
            expires_at=expires_at,
            created_by="chat"
        )

        # Crear mensaje de feedback legible
        rule_text_nl = (
            f"Rule Created: {rule_text} "
            f"(Priority: {priority}, Expires: {expires_at or 'N/A'})\n"
            f"Energy Impact: {energy_impact}"
        )

        return rule_text_nl
    except Exception as e:
        logger.exception("Error invoking chat commander agent: %s", e)
        return {"status": "ERROR", "reason": f"Agent invocation failed: {e}"}