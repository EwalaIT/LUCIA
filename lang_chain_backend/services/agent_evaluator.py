# services/agent_evaluator.py
from __future__ import annotations

import logging
import json
import asyncio
import re
from typing import Optional, Any, Dict

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from db.decisions import get_decision_by_id
from db.rules import get_active_rules
from db.decisions import update_decision_with_proposals, update_decision_status, update_decision_rule_status
from .db_tools import create_rule_tool, modify_rule_tool, delete_rule_tool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _build_rule_generation_prompt(decision_pkg: dict, user_score: float, user_note: str) -> str:
    """
    Builds the system instruction for the Rule Generation Agent.
    Instructs the LLM to analyze the decision performance and propose rule changes.
    """
    active_rules = get_active_rules()
    
    # Formateo mejorado de reglas para incluir EXPIRATION, que es clave en la jerarquía
    rules_text = "\n".join([
        f"Rule ID {r['id']} | Priority: {r['priority']} | Expires: {r.get('expires_at', 'NEVER')} | Rule: {r['rule_text']}" 
        for r in active_rules
    ])
    
    decision_pkg_json = json.dumps(decision_pkg, indent=2, ensure_ascii=False)
    
    prompt = f"""
        ### SYSTEM ROLE: RULE OPTIMIZATION ENGINE

        You are the **System Rule Improvement Agent**. Your core mission is **Efficiency and Optimization**. You must analyze the decision failure and user feedback to propose precise, non-contradictory rule changes that ensure the system operates with **maximum energy efficiency and minimum user discomfort**.

        **STRATEGIC CONTEXT:**
        The rules you manage have a direct impact on energy consumption (e.g., HVAC, lighting). Your primary goal is to **reduce energy consumption without compromising comfort or safety**. Focus ONLY on energy efficiency, HVAC, lighting, occupancy, and comfort. Do NOT propose rules unrelated to these metrics. 
        For example, if the user states, "there IS occupancy," and heating was shut off, the error is severe and requires immediate, high-priority rule correction.
        
        ### RULE DOMAIN SCOPE (STRICT)
        You can ONLY create or modify rules related to:
        - Occupancy detection
        - HVAC setpoints and operation
        - Lighting control and switches
        - Energy consumption reduction
        - Temperature / humidity ranges
        - Harmonization between neighboring zones
        - Time-based schedules for energy optimization

        You are FORBIDDEN from creating rules related to:
        - IT, support processes, user reports, incident escalation
        - Human workflows or organizational procedures
        - Security, HR, or administrative processes
        - Anything not physically measurable by sensors or controllable via actuators
        
        ### RULE TEMPLATING (MANDATORY)
        Every created or modified rule MUST follow this pattern:

        "When <SENSOR CONDITION> THEN <ACTION ON HVAC/LIGHTS> BECAUSE <ENERGY/COMFORT RATIONALE>."

        Examples of valid patterns:
        - "When occupancy_count == 0 for 5 minutes, turn off the lights in the zone because it reduces energy waste."
        - "When temperature exceeds upper comfort band, reduce HVAC setpoint by 1°C to maintain comfort and save energy."

        Invalid patterns:
        - Any rule referencing IT incidents, human tasks, or administrative workflows.
        - Any rule outside the measurable domain of HVAC, lighting, occupancy, or energy metrics.

        ### VALIDATION REQUIREMENTS
        Before proposing any rule:
        1. Verify that the rule affects ONLY entities the system can control (HVAC, switches, sensors).
        2. Verify that the rule uses ONLY measurable signals (occupancy, temp, humidity, time, device states).
        3. If the user feedback indicates a mistaken assumption about occupancy, DO NOT create a new rule unless the failure is repeatable.
        4. Confirm no contradictions with existing rules; prefer MODIFY over CREATE for minor adjustments.
        5. If no valid correction is needed, return rule_proposals: [].

        ### RULE PRIORITY ENFORCEMENT
        - Immediate rules MUST override Mid-Term and Long-Term rules.
        - Mid-Term rules can adjust settings based on trends but never override Immediate rules.
        - Long-Term rules suggest optimization targets but are secondary to real-time occupancy and comfort.

        ### NON-NEGOTIABLE OUTPUT REQUIREMENT
        1. **MUST RETURN RAW JSON:** Your FINAL and ONLY output **MUST BE** one RAW JSON object. NO Markdown, NO conversational text, NO preceding or trailing characters.
        2. **MANDATORY TOOL USE:** You **MUST** use the provided tools (`propose_create_rule`, `propose_modify_rule`, `propose_delete_rule`) if a corrective action is required.
        3. **NO INTERMEDIATE OUTPUT:** Your final response must NOT be an intermediate tool invocation. It must be the **FINAL CONSOLIDATED JSON** containing the *results* of the tool calls.

        ### MANDATORY OUTPUT FORMAT (EXACT JSON SCHEMA)
        You must return exactly this JSON structure. Note the double curly braces for escaping the JSON within the f-string:

        {{
        "chain_of_thought": "REQUIRED: A single concise paragraph. Include the root cause diagnosis, rule ID references, and justification for the proposed priority/action, emphasizing how the change improves **Energy Efficiency** or **Reduces User Discomfort**.",
        "rule_proposals": [
            // Each item MUST be an object returned as the result of a tool invocation.
            // If no action is needed, this array MUST be empty: []
        ]
        }}

        ### OPERATIONAL CONTEXT (INPUTS)
        - Decision ID: {decision_pkg.get('id', 'N/A')}
        - Decision Package (JSON): 
        {decision_pkg_json}
        - User Confidence Score: {user_score:.2f} (0.0 = Bad, 1.0 = Perfect)
        - User Note: "{user_note}"

        ### ACTIVE RULES & HIERARCHY
        - **Current Rules:** Analyze Rule ID, Priority, and Expires fields:
        {rules_text}
        - **Hierarchy (Highest to Lowest):** IMMEDIATE > MID_TERM > LONG_TERM.
        - **Editing Rule:** Prefer MODIFY over CREATE for minor adjustments; cite Rule ID. New overriding rules MUST use a strictly higher priority.
 
        ### REQUIRED WORKFLOW (ENGINEERING REASONING)
        1. **DIAGNOSE & CoT (Deep Analysis):** Determine the root cause (missing rule, wrong priority, conflict, etc.). Your analysis **MUST** link the failure to the **energy goal** (e.g., "The system incorrectly assumed vacancy, leading to unnecessary energy savings at the expense of comfort, or, conversely, wasted energy by over-heating/cooling.").
        2. **ACT (MANDATORY TOOL INVOCATION):** Invoke the necessary tool(s) for the correction:
            - `propose_create_rule(rule_text, priority, expires_at)`
            - `propose_modify_rule(rule_id, rule_text, priority, expires_at)`
            - `propose_delete_rule(rule_id)`
        3. **RETURN:** Output **ONLY** the RAW JSON object that matches the structure in the MANDATORY OUTPUT FORMAT block.

        ---
        **FINAL INSTRUCTION:** Execute the workflow precisely. Base your reasoning on energy optimization and user comfort. Return ONLY the final structured JSON output.
        
        FINAL CHECK: Propose ONLY rules related to HVAC, temperature, lighting, occupancy, energy optimization. Ignore any unrelated domain.

    """
    return prompt

def create_evaluator_agent(llm: BaseLanguageModel):
    """
    Crea un agente evaluador exactamente igual que create_decisor_agent:
    - LLM.bind_tools()
    - Sin ReAct
    - Sin AgentExecutor
    - Devuelve un Runnable
    """
    tools=[create_rule_tool, modify_rule_tool, delete_rule_tool]

    try:
        llm_with_tools = llm.bind_tools(tools)
        logger.info("✅ Evaluator Agent (LLM + Tools) creado correctamente.")
        return llm_with_tools

    except Exception as e:
        logger.exception("❌ Error al crear el Evaluator Agent: %s", e)
        raise


async def run_evaluator(app, decision_id: int, user_score: int, user_note: str):
    """
    Carga la decisión y el feedback, llama al LLM para generar propuestas de reglas 
    usando las herramientas, y devuelve las propuestas.
    """
    
    llm_with_tools = getattr(app.state, "agents", {}).get("evaluator")
    
    if llm_with_tools is None:
        raise RuntimeError("Evaluator Agent is not initialized.")
    
    row = get_decision_by_id(decision_id)
    if not row:
        raise ValueError("Decision not found")
        
    dp_json = row.get("decision_package_json")
    try:
        decision_pkg = json.loads(dp_json)
    except Exception:
        decision_pkg = {"raw": dp_json}
    
    # 1) Construir el prompt de reglas
    system_instruction = _build_rule_generation_prompt(decision_pkg, user_score, user_note)
    
    input_text = "Using ONLY the operational context, propose rules related to HVAC, lighting, occupancy, and energy efficiency. Do NOT propose any IT, workflow, or user incident rules. Return FINAL JSON only using the mandatory output format."
    
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content=input_text),
    ])
    
    logger.info("Esta es la instrucción del Evaluator Agent:\n%s", system_instruction)
    
    agent_chain = prompt_template | llm_with_tools
    
    logger.info("Este es el agent_chain configurado para el agente:", agent_chain)
    
    try:
        # 2) Invoke LLM
        raw_output = await asyncio.to_thread(
            lambda: agent_chain.invoke({"input": input_text})
        )
        
        llm_response_text = raw_output.content
        logger.info("Respuesta cruda del Agente:\n%s", llm_response_text)
        
        # 3) Extract JSON Robustly (The fix for the issue)
        response_json = _extract_json_from_text(llm_response_text)
        
        chain_of_thought = response_json.get("chain_of_thought", "No COT provided.")
        proposals = response_json.get("rule_proposals", [])

        return {
            "chain_of_thought": chain_of_thought,
            "rule_proposals": proposals
        }
        
    except Exception as e:
        logger.exception("Error calling LLM for rule generation: %s", e)
        return {
            "chain_of_thought": f"ERROR: Falló la generación de reglas: {e}",
            "rule_proposals": []
        }


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Attempts to extract the required final JSON structure, handling raw JSON, 
    markdown wrappers, or intermediate function call output from the LLM.
    """
    
    # Clean the text of markdown wrappers first for robustness
    clean_text = re.sub(r'```json\s*|```', '', text, flags=re.DOTALL).strip()
    
    # A. Search for the FINAL JSON structure (Priority 1)
    # Tries to find the main structure: {"chain_of_thought": ... "rule_proposals": ...}
    final_json_match = re.search(r'\{\s*"chain_of_thought".*\}', clean_text, re.DOTALL)

    if final_json_match:
        try:
            final_json_str = final_json_match.group(0)
            result = json.loads(final_json_str)
            if "chain_of_thought" in result and "rule_proposals" in result:
                return result
        except json.JSONDecodeError:
            pass

    # B. Search for an INTERMEDIATE TOOL CALL (Priority 2 - Fallback)
    # Looks for a single tool call object: {"name": "propose_...", "parameters": ...}
    # This handles the case where the LLM stops at the tool call step.
    tool_call_match = re.search(r'\{\s*"name"\s*:\s*"(propose_(create|modify|delete)_rule)"', clean_text)
    
    if tool_call_match:
        try:
            # Find start of JSON object
            start_idx = tool_call_match.start()
            potential_json = clean_text[start_idx:]
            
            # Simple heuristic: find matching brace (not perfect but robust enough for structured tool output)
            depth = 0
            end_idx = -1
            for i, char in enumerate(potential_json):
                if char == '{': depth += 1
                elif char == '}': depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break
            
            if end_idx != -1:
                tool_call_str = potential_json[:end_idx]
                tool_call_obj = json.loads(tool_call_str)
                
                # Transform Tool Call format (LangChain/Ollama specific) to our internal Rule Proposal format
                # The tool call usually has "parameters": { ... } which contains our rule fields
                proposal = tool_call_obj.get("parameters", {})
                # We add the action_type based on the tool name if missing
                tool_name = tool_call_obj.get("name", "")
                
                if "create" in tool_name: proposal["action_type"] = "CREATE"
                elif "modify" in tool_name: proposal["action_type"] = "MODIFY"
                elif "delete" in tool_name: proposal["action_type"] = "DELETE"

                return {
                    "chain_of_thought": "WARNING: LLM returned intermediate tool call only. CoT inferred from tool execution.",
                    "rule_proposals": [proposal]
                }
        except Exception as e:
            logger.warning("Failed to parse intermediate tool call: %s", e)

    # C. Default Fallback Error
    return {
        "chain_of_thought": f"ERROR: Failed to extract final or intermediate JSON structure. Raw output starts with: {text[:200]}...",
        "rule_proposals": []
    }

# -------------------------
# Worker asíncrono para evaluación en background
# -------------------------
_evaluator_task: Optional[asyncio.Task] = None


async def _evaluator_loop(app) -> None:
    """
    Bucle principal del worker que procesa la cola de decisiones
    para generar propuestas de reglas.
    """
    queue: asyncio.Queue = app.state.eval_queue
    logger.info("Rule Generation Evaluator loop started.")
    
    try:
        while True:
            decision_item = await queue.get()
            
            # Si tiene score y note, es el feedback del usuario
            if "user_score" in decision_item and "user_note" in decision_item:
                decision_id = decision_item["decision_id"]
                try:
                    update_decision_rule_status(decision_id, rule_status="IN_PROGRESS")
                    # NOTA: Llamar a la función que genera las reglas
                    proposals = await run_evaluator(
                        app,
                        decision_id=decision_id,
                        user_score=decision_item["user_score"],
                        user_note=decision_item["user_note"]
                    )
                    
                    chain_of_thought = proposals.get("chain_of_thought", "")
                    rule_proposals_list = proposals.get("rule_proposals", [])
                    
                    if not rule_proposals_list and "ERROR:" in chain_of_thought:
                        # Fallo capturado dentro de run_evaluator
                        raise RuntimeError(f"Rule generation failed. CoT: {chain_of_thought}")
                    
                    rule_proposals_json_str = json.dumps(rule_proposals_list)
                    

                    update_decision_with_proposals(
                        decision_id=decision_id,
                        proposals_json=rule_proposals_json_str,
                        chain_of_thought=chain_of_thought
                    )
                    
                    update_decision_rule_status(decision_id, "RULES_READY")
                    
                    logger.info(
                        f"✅ Stored proposals for Decision {decision_id}: {len(rule_proposals_list)} proposals."
                    )
                     
                    logger.info("Rule proposals generated for Decision %s: %s", decision_item["decision_id"], proposals)

                except Exception as e:
                    logger.exception(f"❌ Critical Error processing user feedback for Decision {decision_id}: {e}")
                    update_decision_rule_status(decision_id, "RULES_FAILED")
            
                finally:
                    queue.task_done()

    except asyncio.CancelledError:
        logger.info("Evaluator loop cancelled.")
    except Exception as e:
        logger.exception("Unexpected error in evaluator loop: %s", e)
        

async def start_evaluator_loop(app) -> None:
    """
    Inicializa la cola de evaluación y lanza el worker en background.
    """
    global _evaluator_task
    if hasattr(app.state, "eval_queue"):
        logger.warning("Evaluator queue already exists, skipping creation.")
    else:
        app.state.eval_queue = asyncio.Queue()
        logger.info("Evaluator queue initialized.")

    if _evaluator_task is None or _evaluator_task.done():
        _evaluator_task = asyncio.create_task(_evaluator_loop(app))
        logger.info("Evaluator background task started.")
    else:
        logger.warning("Evaluator background task already running.")


async def stop_evaluator_loop() -> None:
    """
    Cancela la tarea del worker de evaluación.
    """
    global _evaluator_task
    if _evaluator_task is not None and not _evaluator_task.done():
        _evaluator_task.cancel()
        try:
            await _evaluator_task
        except asyncio.CancelledError:
            logger.info("Evaluator task cancelled successfully.")
    _evaluator_task = None