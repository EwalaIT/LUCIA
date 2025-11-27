# services/agent_decisor.py
import logging
import asyncio
import json
from typing import Optional, Any, Dict
from datetime import datetime, timezone

from config import settings
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

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


def _build_prompt(rules_context: str, current_time: str) -> str:
    """
    Builds the dynamic system prompt for the Energy Efficiency Decisor Agent.
    
    Args:
        rules_context (str): A natural language string containing active rules and schedules.
        current_time (str): The current ISO timestamp and Day of Week.
    """
    return f"""
        ### ROLE & OBJECTIVE
        You are the **Lead Energy Efficiency & Control Orchestrator** for an Intelligent Building.
        Your goal is to optimize energy consumption while strictly maintaining comfort standards defined by the active rules.
        You operate in a backend loop. Your output is read by a machine, not a human.

        ### OPERATIONAL CONTEXT
        - **Current System Time:** {current_time}
        - **Active Rules & Schedules (Highest Priority):**
        {rules_context}
        
        ### CONTEXT FACTORS TO CONSIDER
        For every decision, you MUST analyze the following factors against the active rules:
        1. **Temperature/Humidity Sensors (e.g., `sensor.out_temperature`):** Use actual environmental conditions.
        2. **Actuators & Switches (e.g., `switch.office_1_switch`):** Check the state (`on/off`) of all non-climate power switches. Use `turn_on` or `turn_off` for these.
        3. **Climate Entities (e.g., `climate.thermostat_r_d_i`):** Check the current operation (`heat/off`) and the `current_temperature` vs. the `temperature` setpoint. Use `set_temperature` for adjustments.
        4. **Occupancy Status:** Infer presence (or lack thereof) from available sensors or external context (e.g., `Office 1 Switch` is `off` suggests no occupancy/activity). **Efficiency priority is extremely high when zones are inferred to be empty.**
        5. **Schedule & Bounds:** Apply the time-based rules (`start_time`/`end_time`) and the prescribed temperature limits (`temp_min`/`temp_max`) from the rules context.

        ### DECISION HIERARCHY (Order of Precedence)
        1. **SAFETY:** Never execute an action that endangers equipment or humans.
        2. **SHORT-TERM RULES:** Immediate overrides provided in the context above.
        3. **SCHEDULES/MID-TERM RULES:** Standard operating windows.
        4. **GENERAL EFFICIENCY:** If no rule forbids it, optimize for lowest energy use.

        ### TOOLS & PROTOCOL
        You have access to the **Decision Safety Check Tool**.
        1. **Data Analysis:** The current state and context are provided below. Analyze this data against 'Active Rules'.
        2. **Formulation:** Define necessary actions (if any) in the `suggested_actions` list.
        3. **Verification (MANDATORY for ACTION):** If `decision_type` is **ACTION**, you MUST call the `safety_check` tool with the *entire proposed DecisionPackage JSON* as input before finalizing.
        4. **Final Output (MANDATORY):** Your last response MUST ONLY be the **RAW JSON Object** of the DecisionPackage.

        ### OUTPUT FORMAT SPECIFICATION
        Your final response must be a **RAW JSON Object** (no markdown formatting, no ```json wrappers).
        Structure:
        {{{{
        "chain_of_thought": "REQUIRED: Step-by-step reasoning citing specific rules ID or sensor values that justifies the entire decision. MUST BE PRESENT.",
        "decision_type": "ACTION" | "NO_ACTION",
        "suggested_actions": [
            {{{{
            "action": "turn_off | set_temperature | ...",
            "target_entity": "entity_id",
            "parameters": {{{{ "value": ... }}}},
            "rationale": "Direct compliance with Rule #2 regarding office hours."
            }}}}
        ],
        "confidence": 0.0 to 1.0,
        "goal": "Brief summary of what this decision achieves"
        }}}}
    """

def create_decisor_agent(llm: BaseLanguageModel):
    """
    Crea y devuelve un agente decisor basado en LangChain v1.x.
    Usa el método canónico create_agent, que devuelve un Runnable.
    """
    system_prompt = ("You are the Lead Energy Efficiency & Control Orchestrator for an Intelligent Building. "
        "You analyze rules, sensor values, and contexts to propose actions "
        "that optimize heating, cooling, lighting and energy efficiency.")

    tools = [
        # get_current_state_tool,
        # call_service_tool,
        # vlm_fetch_tool,
        safety_check_tool,
    ]

    try:
        llm_with_tools = llm.bind_tools(tools)

        logger.info("✅ Decisor Agent (LLM + Tools) creado correctamente.")
        return llm_with_tools

    except Exception as e:
        logger.exception("❌ Error al crear el Decisor Agent: %s", e)
        raise


async def run_decisor(app, ha_instance: str, context: dict, reason: str = "observation", rules_context: str = "",) -> Optional[Dict[str, Any]]:
    """
    Asynchronously run the Decisor agent, persist the produced decision, and return a dict:
    { "decision_id": int, "decision_package": dict }
    """
    llm_with_tools = getattr(app.state, "agents", {}).get("decisor")

    current_time = datetime.now(timezone.utc).isoformat()
    dynamic_prompt = _build_prompt(rules_context, current_time)
     
    if not llm_with_tools:
        logger.error("Decisor agent (LLM+Tools) not available in app.state.agents")
        return None
    
   # --- 1. Formatear el contexto de la entidad ---
    formatted_context_str = _format_context_for_agent(context)
    
    logger.info("This is the context formated: %s", formatted_context_str)

    # --- 2. Crear el Prompt Template (en cada ciclo) ---
    # Usamos el dynamic_prompt_spec como el System Prompt para inyectar todas las reglas y especificaciones
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", dynamic_prompt),
        # El mensaje humano solo contiene el contexto de la invocación
        ("human", "{input}"),
    ])

    # --- 3. Construir la cadena completa del Agente para esta invocación ---
    agent_chain = prompt_template | llm_with_tools
    
    # --- 4. Construir el input para el mensaje 'human' ---
    input_text = (
        f"Trigger reason: {reason}\n"
        f"HA instance: {ha_instance}\n"
        f"Context snapshot:\n{formatted_context_str}\n"
        "Produce a DecisionPackage JSON as specified."
    )

    # Invoke the agent in thread to avoid blocking
    try:
        # La cadena (prompt | llm_with_tools) espera un dict con la clave 'input'
        result = await asyncio.to_thread(lambda: agent_chain.invoke({"input": input_text}))
    except Exception as e:
        logger.exception("Error invoking decisor agent: %s", e)
        return None
    
    raw = ""
    
    # 1. Intentar acceder al atributo 'content' (típico de AIMessage)
    if hasattr(result, "content"):
        raw = result.content
    # 2. Si es un diccionario (menos común, pero manejamos)
    elif isinstance(result, dict) and 'output' in result:
        raw = result['output']
    # 3. Fallback a string
    else:
        raw = str(result)
        
    # 4. Limpieza (Ollama a veces añade basura antes o después del JSON)
    # Buscamos y extraemos el bloque JSON si el modelo falló en modo `format="json"`.
    # Esto es manejado por _extract_json_from_text, pero forzamos la conversión a str primero.
    if not isinstance(raw, str):
        raw = str(raw)

    # Try to extract JSON from raw text
    try:
        dp = _extract_json_from_text(raw)
    except Exception as e:
        logger.exception("Failed to extract DecisionPackage JSON from agent output: %s", e)
        # persist a raw fallback decision so operator can inspect
        raw_pkg = {"raw_output": raw, "chain_of_thought": "Failed to parse valid JSON from LLM output."}
        dp_json_str = json.dumps(raw_pkg, ensure_ascii=False)
        
        action_summary = "Parsing failed: RAW OUTPUT stored."
        
        decision_id = persist_new_decision(
            decision_package_json=dp_json_str,
            goal="Failed to parse decision package",
            reasoning=raw_pkg.get("chain_of_thought"),
            confidence=None,
            status="PENDING",
            action_summary=action_summary,
            target_entity=None,
            executed_action=None,
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
    actions = dp.get("suggested_actions", [])
    
    if actions and dp.get("decision_type") == "ACTION":
        # Usamos la primera acción para la BBDD
        first_action = actions[0]
        target_entity = first_action.get("target_entity")
        executed_action = first_action.get("action")
        # Creamos un resumen simple
        action_summary = f"{executed_action} on {target_entity}"
    elif dp.get("decision_type") == "NO_ACTION":
        action_summary = "NO_ACTION determined by LLM."
        target_entity = None
        executed_action = None
    else:
        action_summary = f"Unknown decision type: {dp.get('decision_type')}"
        target_entity = None
        executed_action = None
        
    # Persist decision
    try:
        dp_json_str = json.dumps(dp, ensure_ascii=False)
        decision_id = persist_new_decision(
            decision_package_json=dp_json_str,
            goal=dp.get("goal"),
            reasoning=dp.get("chain_of_thought"),
            confidence=dp.get("confidence"),
            status="PENDING",
            # NUEVOS CAMPOS
            action_summary=action_summary,
            target_entity=target_entity,
            executed_action=executed_action,
        )
    except Exception as e:
        logger.exception("Failed to persist decision: %s", e)
        return None

    return {"decision_id": decision_id, "decision_package": dp}


def _extract_json_from_text(raw: str) -> dict:
    """
    Extracts the FIRST valid JSON object from text using brace-scanning.
    This handles nested objects and random text before/after.
    """
    start = raw.find("{")
    if start == -1:
        raise ValueError("No opening '{' found in LLM output.")

    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = raw[start:i+1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    break  # try next possible JSON

    raise ValueError(f"Could not extract JSON object from: {raw[:200]}")


def _format_context_for_agent(full_context: Dict[str, Any]) -> str:
    """
    Simplifica el diccionario de contexto completo (estado actual + memoria)
    a un string estructurado en lenguaje natural para el Agente Decisor.
    """
    lines = []

    # --- A) ESTADO ACTUAL SIMPLIFICADO ---
    current_state = full_context.get("current_state", {})
    lines.append("=== CURRENT ENTITY STATES ===")

    for entity_id, ha_data in current_state.items():
        if not isinstance(ha_data, dict):
            # Caso fallback: si solo se pasó el estado
            lines.append(f"- **{entity_id}**: State: {ha_data}")
            continue

        state = ha_data.get("state", "unknown")
        attrs = ha_data.get("attributes", {})

        # Extracción de atributos clave para el LLM
        unit = attrs.get("unit_of_measurement", "")
        friendly_name = attrs.get("friendly_name", entity_id)

        # Datos extra relevantes para el LLM (ej. temperatura objetivo, ocupación)
        extra_data = []
        if 'temperature' in attrs and entity_id.startswith("climate"):
            extra_data.append(f"Set: {attrs['temperature']}°C")
        if 'current_temperature' in attrs and entity_id.startswith("climate"):
            extra_data.append(f"Current: {attrs['current_temperature']}°C")

        extra_str = f" ({', '.join(extra_data)})" if extra_data else ""

        lines.append(f"- **{friendly_name}** ({entity_id}): **State: {state} {unit}**{extra_str}")

    # --- B) HISTORIAL DE DECISIONES SIMPLIFICADO ---
    history = full_context.get("history", [])
    if history:
        lines.append("\n=== RECENT HISTORY (Observation -> Decision) ===")
        # Mostrar solo las 3 entradas más recientes
        for entry in history[-3:]:
            obs_state = entry.get("observation", {}).get("current_state", {})
            decision_id = entry.get("decision_id", "N/A")
            timestamp = entry.get("timestamp", "N/A")

            # Simple summarization of the observation
            temp_status = next(
                (f"Temp: {obs.get('state')}" for ent, obs in obs_state.items() if 'temp' in ent), 
                "N/A"
            )

            lines.append(f"[{decision_id}] {timestamp}")
            lines.append(f"  Obs: {temp_status} | Dec: {entry.get('goal', 'Optimization')}")
    else:
        lines.append("\n=== RECENT HISTORY (Observation -> Decision) ===\n- No historical context available.")

    return "\n".join(lines)