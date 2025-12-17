import logging
import json
import datetime
from typing import Dict, Any, Optional

from langchain_core.tools import tool
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from difflib import get_close_matches

# Importa tus módulos reales (ajusta las rutas si es necesario)
from services.ha_tools import HomeAssistantAPI
from db.rules import get_active_rules, create_new_rule, modify_existing_rule, delete_rule_by_id


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Instancia de Home Assistant Client
ha = HomeAssistantAPI()

# ============================================================
# UTILITY: RULE DB IMPLEMENTATION & STATE BUILDER
# ============================================================

def build_natural_language_state(raw_states: Dict[str, Dict[str, Any]]) -> str:
    """
    Converts Home Assistant states to a detailed, structured natural language summary, 
    including friendly names and relevant attributes for the LLM.
    (Refactored to follow the structure of _format_context_for_agent)
    """
    lines = []
    lines.append("=== HOME ASSISTANT ENTITY STATES SUMMARY ===")

    for entity_id, ha_data in raw_states.items():
        if not isinstance(ha_data, dict):
            lines.append(f"- **{entity_id}**: State: {ha_data}")
            continue

        state = ha_data.get("state", "unknown")
        attrs = ha_data.get("attributes", {})

        # 1. Basic data extraction
        friendly_name = attrs.get("friendly_name", entity_id.replace("_", " ").title())
        unit = attrs.get("unit_of_measurement", "")

        # 2. Domain-specific extra data
        extra_data = []

        if entity_id.startswith("climate."):
            # Target and current temperature
            if 'temperature' in attrs:
                extra_data.append(f"Set: {attrs['temperature']}°C")
            if 'current_temperature' in attrs:
                extra_data.append(f"Current: {attrs['current_temperature']}°C")
            # HVAC Action
            hvac_action = attrs.get("hvac_action")
            if hvac_action and hvac_action != state:
                extra_data.append(f"Mode: {hvac_action}")

        elif entity_id.startswith("light."):
            # Brightness level in percentage
            br = attrs.get("brightness")
            if br is not None and isinstance(br, (int, float)):
                percent = round((br / 255) * 100)
                extra_data.append(f"Brightness: {percent}%")

        elif entity_id.startswith("input_text.") and entity_id.endswith("_count"):
            # Specific case for counters
            extra_data.append(f"Counter value: {state}")
            state = "" # Clear state to avoid duplication if it is already in extra_data

        elif unit and state != "unknown":
            # Case for sensors that are not climate and have a unit
            pass # Already handled in the final line, no extra_data needed unless there is a special attribute

        # 3. Build the final line
        extra_str = f" ({', '.join(extra_data)})" if extra_data else ""
        
        if state or extra_str:
            # Format: - **Friendly Name** (entity_id): State: state unit (extra attributes)
            status_part = f"**State: {state} {unit}**" if state else ""
            lines.append(f"- **{friendly_name}** ({entity_id}): {status_part}{extra_str}")
        else:
            lines.append(f"- **{friendly_name}** ({entity_id}): Unknown Status")

    return "\n".join(lines)
    


# ============================================================
# PLACEHOLDERS Y WRAPPERS DE REGLAS (Mantenidas)
# ============================================================

def create_rule_tool(rule_text: str, priority: str = "MID_TERM", expires_at: Optional[str] = None) -> Dict[str, Any]:
    if priority == "IMMEDIATE" and not expires_at:
        return {"status": "FAILED", "reason": "IMMEDIATE rules require an 'expires_at' timestamp."}

    rule_id = create_new_rule(
        rule_text=rule_text,
        priority=priority.lower(),
        expires_at=expires_at,
        created_by="agent"
    )

    return {
        "status": "CREATED",
        "rule_id": rule_id,
        "rule_text": rule_text,
        "priority": priority,
        "expires_at": expires_at
    }

def modify_rule_tool(rule_id: int, new_rule_text: str, new_priority: str = "MID_TERM", expires_at: Optional[str] = None) -> Dict[str, Any]:
    if new_priority.upper() == "IMMEDIATE" and not expires_at:
        return {
            "status": "FAILED",
            "reason": "IMMEDIATE rules require an 'expires_at' timestamp."
        }
    
    modified = modify_existing_rule(
        rule_id=rule_id,
        new_rule_text=new_rule_text,
        new_priority=new_priority.lower(),
        expires_at=expires_at
    )

    if not modified:
        return {"status": "FAILED", "reason": "Rule not found or not active"}

    return {
        "status": "MODIFIED",
        "rule_id": rule_id,
        "new_rule_text": new_rule_text,
        "new_priority": new_priority,
        "expires_at": expires_at
    }

def delete_rule_tool(rule_id: int) -> Dict[str, Any]:
    deleted = delete_rule_by_id(rule_id)

    if not deleted:
        return {"status": "FAILED", "reason": "Rule not found or already inactive"}

    return {
        "status": "DELETED",
        "rule_id": rule_id
    }


# ============================================================
# HOME ASSISTANT ACTION TOOLS (Ejecución Directa) ⚡
# ============================================================
class ActionExecutorSchema(BaseModel):
    action_type: str = Field(description="The type of HA service call: 'turn_on', 'turn_off', or 'set_temperature'.")
    entity_id: str = Field(description="The Home Assistant entity ID to target (e.g., 'light.office_lights', 'climate.office_thermostat, 'switch.office1').")
    temperature: Optional[float] = Field(description="MANDATORY only if action_type is 'set_temperature'. The target temperature (e.g., 22.5).")
    
def execute_safe_action_wrapper(action_type: str, entity_id: str, temperature: Optional[float]) -> str:
    """Wrapper for direct HA service calls, now consolidated."""
    
    data: Dict[str, Any] = {}
    service: str = action_type
    
    if action_type == "set_temperature":
        if temperature is None:
             return f'{{"status": "FAILED", "reason": "Action type set_temperature requires the temperature parameter."}}'
        data["temperature"] = temperature
        domain = "climate"
    elif action_type in ["turn_on", "turn_off"]:
        domain = entity_id.split(".")[0]
    else:
        return f'{{"status": "FAILED", "reason": f"Unknown action_type: {action_type}"}}'
        
    try:
        logger.info(f"Direct HA Call: Domain={domain}, Service={service}, Entity={entity_id}, Data={data}")

        # Ejecución de la acción real
        result = ha.call_service(domain, service, entity_id, data)
        
        # Opcional: Persistir la acción como regla inmediata (con expiración corta)
        # Esto implementa tu idea de "guardar como regla a corto plazo"
        try:
             rule_text = f"User executed an immediate command: {action_type} on {entity_id} with data {data}"
             # Nota: Debes implementar create_rule en db.rules para esto:
             # create_rule(rule_text=rule_text, priority="IMMEDIATE", expires_at=(datetime.now() + timedelta(minutes=5)).isoformat())
             logger.info(f"Action persisted as an IMMEDIATE rule: {rule_text}")
        except Exception as rule_e:
             logger.warning(f"Could not persist action as rule: {rule_e}")
        
        return json.dumps({"status": "SUCCESS", "action": f"{service} on {entity_id}", "result": result}, ensure_ascii=False)
    except Exception as e:
        logger.exception(f"Error executing HA service {service} for {entity_id}: {e}")
        return f'{{"status": "FAILED", "reason": "Failed to execute HA action due to internal error: {e}"}}'
    
execute_safe_action_tool = StructuredTool.from_function(
    func=execute_safe_action_wrapper,
    name="execute_safe_action_tool",
    description="Executes a verified immediate control action (turn_on, turn_off, set_temperature) on a Home Assistant entity. This tool should ONLY be called AFTER the agent has internally confirmed the action does NOT contradict any active rules and is safe.",
    args_schema=ActionExecutorSchema
)


async def execute_safe_action_fn(action_type: str, user_entity_name: str, domain: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Handles an immediate action requested by the user.
    Resolves entities, checks for rule conflicts, creates a rule if needed,
    and executes the action safely.
    """

    # Fetch all current entities and states from Home Assistant
    ha_states = await ha.get_states() 
    # 1. Resolve entity_id using fuzzy matching
    entity_ids = list(ha_states.keys())
    matches = get_close_matches(user_entity_name, entity_ids, n=1, cutoff=0.5)
    if not matches:
        return {"error": f"No entity found matching '{user_entity_name}'."}
    entity_id = matches[0]

    # 2. Check active rules
    active_rules = get_active_rules()
    conflicting_rules = []
    for rule in active_rules:
        if entity_id in rule["rule_text"]:  # simple string check, can mejorar
            conflicting_rules.append(rule)

    # 3. Determine if we need to create a rule (immediate order)
    # This assumes any action_type requested by user is to become a rule
    # Prompt the user for expires_at outside of this function
    expires_at = datetime.utcnow().isoformat()  # default, replace with user input
    priority = "immediate"

    # Optionally, check conflicts with rules here
    # For now, we just log them
    if conflicting_rules:
        logger.info(f"Found {len(conflicting_rules)} conflicting rules for {entity_id}")

    # 4. Create rule in DB
    rule_text = f"{action_type} {entity_id}"
    rule_id = create_new_rule(rule_text=rule_text, priority=priority, expires_at=expires_at, created_by="user")
    logger.info(f"Created new rule ID={rule_id}: {rule_text} with expires_at={expires_at}")

    # 5. Execute action via HA service
    if not domain:
        # Infer domain from entity_id prefix (light.*, switch.*, etc.)
        domain = entity_id.split(".")[0]
    resp = ha.call_service(domain=domain, service=action_type, entity_id=entity_id, params=params)

    # Return structured JSON for Gemma3
    return {{
        "raw_tool_invocation":{ {
            "name": "execute_safe_action_tool",
            "parameters": {{
                "action_type": action_type,
                "entity_id": entity_id,
                "rule_id": rule_id,
                "expires_at": expires_at,
                "domain": domain,
                "params": params or {},
                "ha_response": resp,
            }}
        }}
    }}
    
class ExecuteSafeActionInput(BaseModel):
    action_type: str = Field(..., description="HA action to execute, e.g., turn_on, turn_off")
    user_entity_name: str = Field(..., description="The entity name or friendly name given by the user")
    domain: Optional[str] = Field(default=None, description="HA domain (light, switch, etc.)")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional HA service parameters")

execute_safe_action_tool = StructuredTool.from_function(
    func=execute_safe_action_fn,
    name="execute_safe_action_tool",
    description="Resolves entity, checks rules, creates a rule if needed, and executes a safe HA action. Inputs: action_type, user_entity_name, domain (optional), params (optional)."
)
    
# ============================================================
# STATE AND RULE TOOLS
# ============================================================

@tool
def get_full_state_tool() -> str:
    """
    Returns a JSON string containing the raw Home Assistant states of selected entities and a natural language summary.
    Use this to get the current status of the building's infrastructure (lights, temperature, etc.).
    
    Returns:
        A JSON string like: {"raw": {...}, "natural_language": "..."}
    """
    try:
        raw = ha.get_states()
        nl = build_natural_language_state(raw)
        return json.dumps({"raw": raw, "natural_language": nl}, ensure_ascii=False)
    except Exception as e:
        logger.exception(f"Error getting full state: {e}")
        return f'{{"status": "ERROR", "reason": "Failed to retrieve full state due to an internal system error: {e}"}}'

@tool
def get_rules_tool() -> str:
    """
    Returns a JSON string containing a list of all active system rules and policies.
    Each rule includes its ID, rule_text, and priority. Use this tool before
    proposing rule changes (create, modify, delete) to check for existing rules.
    """
    rules = get_active_rules()
    return json.dumps({"rules": rules}, ensure_ascii=False)

# ============================================================
# PYDANTIC SCHEMAS Y LISTA FINAL DE TOOLS
# ============================================================

class CreateRuleSchema(BaseModel):
    rule_text: str = Field(description="Natural language description of the rule to create (e.g., 'Turn off heating if the outside temperature is above 18C').")
    priority: str = Field(description="Rule priority: 'IMMEDIATE', 'MID_TERM', or 'LONG_TERM'. IMMEDIATE rules are high-priority but must have an expiration date.")
    expires_at: Optional[str] = Field(description="Optional ISO timestamp (YYYY-MM-DDTHH:MM:SSZ) for rule expiration. MANDATORY if priority is IMMEDIATE.")

class ModifyRuleSchema(BaseModel):
    rule_id: int = Field(description="The unique integer ID of the rule to modify.")
    new_rule_text: str = Field(description="The new natural language description of the rule.")
    new_priority: str = Field(description="The new priority level: 'IMMEDIATE', 'MID_TERM', or 'LONG_TERM'.")
    expires_at: Optional[str] = Field(description="Optional new ISO timestamp for rule expiration. MANDATORY if new_priority is IMMEDIATE.")

class DeleteRuleSchema(BaseModel):
    rule_id: int = Field(description="The unique integer ID of the rule to delete.")


def get_all_tools():
    """
    Returns the complete list of tools for the agent.
    """
    rule_proposal_tools = [
        StructuredTool.from_function(
            func=create_rule_tool,
            name="create_rule_tool",
            description="Used to propose creating a new system automation rule or policy.",
            args_schema=CreateRuleSchema
        ),
        StructuredTool.from_function(
            func=modify_rule_tool,
            name="modify_rule_tool",
            description="Used to propose modifying an existing system rule by its ID.",
            args_schema=ModifyRuleSchema
        ),
        StructuredTool.from_function(
            func=delete_rule_tool,
            name="delete_rule_tool",
            description="Used to propose deleting an existing system rule by its ID.",
            args_schema=DeleteRuleSchema
        )
    ]
    
    ha_action_and_state_tools = [
        get_full_state_tool,       
        execute_safe_action_tool,  
        get_rules_tool,           
    ]
    
    return rule_proposal_tools + ha_action_and_state_tools