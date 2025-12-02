# services/agent_evaluator.py
from __future__ import annotations

import logging
import json
import asyncio
from typing import Optional

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

    # return f"""
    #     ### ROLE & OBJECTIVE
    #     You are the **System Rule Improvement Agent**. Your core task is to analyze a past decision's performance based on user feedback (Score/Note) and propose precise, non-contradictory changes to the system's rule set to prevent future suboptimal decisions.

    #     ### OPERATIONAL CONTEXT
    #     - **Decision ID:** {decision_pkg.get('id', 'N/A')}
    #     - **Decision Package (JSON):** {json.dumps(decision_pkg, indent=2, ensure_ascii=False)} (Contains the context and result of the past decision)
    #     - **User Confidence Score:** {user_score:.2f} (0.0=bad, 1.0=perfect)
    #     - **User Note:** "{user_note}"

    #     ### ACTIVE RULES (Current State)
    #     **Analyze these rules carefully. Note the 'Priority' and 'Expires' fields:**
    #     {rules_text}

    #     ### RULE MANAGEMENT HIERARCHY & CONFLICT RESOLUTION
    #     The system uses the following strict hierarchy for rule execution:
    #     1. **IMMEDIATE:** Highest priority (usually short-lived, overriding everything).
    #     2. **MID_TERM:** Medium priority (weeks/months expiration).
    #     3. **LONG_TERM:** Lowest priority (often permanent, baseline rules).

    #     **CONFLICT RESOLUTION:** If two rules contradict, the rule with the **higher priority** is executed. If priorities are equal, the outcome is ambiguous (which you must avoid).

    #     **Your proposed rule changes MUST adhere to these criteria:**

    #     1. **PRIORITY & CONTRADICTION:**
    #     - If a new rule is required to **override** an existing rule (R_existing), the new rule must have a **strictly higher priority** than R_existing (e.g., creating an `immediate` rule to override a `mid_term` one).
    #     - If the new rule **supports/refines** an existing rule, choose the lowest possible priority (`long_term` or `mid_term`) to minimize conflicts, or consider **MODIFYING** the existing rule instead.
    #     - **NEVER** introduce two rules with the same priority that directly contradict each other.

    #     2. **MODIFICATION (Preferred):** If a rule (e.g., R19, R20) exists and only needs a small change (e.g., temperature range or time), **always prefer `propose_modify_rule`** by citing the specific Rule ID.

    #     3. **EXPIRATION:** If a suboptimal decision was caused by a temporary exception, consider setting an `expires_at` date for the new `immediate` or `mid_term` rule to ensure it cleans itself up. Use the format **YYYY-MM-DDTHH:MM:SSZ**.

    #     4. **ELIMINATION:** Only propose deleting a rule if it is fully **obsoleto** or if it is the root cause of the error and cannot be modified effectively.

    #     ### INSTRUCTIONS
    #     1. **Analysis & Diagnosis:** Based on the `User Confidence Score` and `User Note`, determine the exact flaw (missing rule, incorrect priority, too broad a rule) in the existing rule set.
    #     2. **Chain of Thought (CoT):** Detail the exact flow:
    #     - *Diagnosis: Why did the current rule set lead to the decision (cite specific Rule ID(s))?*
    #     - *Proposed Change: What rule action (Create/Modify/Delete) is necessary?*
    #     - *Justification: Why is this priority/modification the correct resolution to the conflict/flaw?*
    #     The CoT must be a **single, clear, and concise paragraph** written for the end-user (non-technical reader).
    #     3. **Proposal Generation:** Use the provided tools (`propose_create_rule`, `propose_modify_rule`, `propose_delete_rule`) to generate the required rule management actions.
    #     4. **Final Output (CRITICAL):** Your last response **MUST ONLY** be the **RAW JSON Object** of the Rule Proposal. It must not contain *any* explanatory text, Markdown wrappers (like ```json), or conversational filler outside of the JSON object itself.

    #     ### MANDATORY OUTPUT FORMAT
    #     Your final output MUST follow this exact RAW JSON structure:
    #     The JSON Object must contain exactly two top-level keys:

    #     KEY 1: "chain_of_thought"
    #        - Type: String
    #        - Content: Detailed reasoning for the proposal.

    #     KEY 2: "rule_proposals"
    #        - Type: List of Objects
    #        - Content: The output objects generated by your tool calls.
           
    #     Structure of objects inside "rule_proposals" list:
    #        - "action_type" (String): One of CREATE, MODIFY, DELETE
    #        - "rule_text" (String): The text of the rule
    #        - "priority" (String): One of immediate, mid_term, long_term
    #        - "expires_at" (String/Null): ISO format date or null
    #        - "rule_id" (Integer/Null): Required for MODIFY/DELETE
    # """
    
    prompt = f"""
        ### ROLE & OBJECTIVE
        You are the System Rule Improvement Agent. Your single, non-negotiable mission is to analyze the provided Decision Package and the user's feedback (score + note), determine the root cause of any suboptimal decision, and propose precise, non-contradictory changes to the system's rule set.

        ---  
        ### CRITICAL EXECUTION REQUIREMENTS (DO NOT OVERRIDE)
        1. Your FINAL output **MUST BE** exactly one RAW JSON object (no markdown, no explanations, no extra text).
        2. You **MUST** use the provided tools to formalize proposals: `propose_create_rule`, `propose_modify_rule`, `propose_delete_rule`.
        3. You **MUST** include a non-empty `chain_of_thought` paragraph in every response, even if `rule_proposals` is empty.
        4. If no action is necessary, return `"rule_proposals": []` and a meaningful `chain_of_thought`.

        ---  
        ### MANDATORY OUTPUT FORMAT (EXACT RAW JSON)
        Return exactly one JSON object with two top-level keys. Example (this is the exact shape you must return; do not add or remove fields):

        {{ 
        "chain_of_thought": "REQUIRED: A single concise paragraph explaining the diagnosis, referencing rule IDs when applicable, and justifying the chosen action(s).",
        "rule_proposals": [
            /* Each item MUST be an object returned as the result of a tool invocation.
            If no proposals are needed, this array MUST be empty: [] */
        ]
        }}

        ---  
        ### OPERATIONAL CONTEXT (INPUTS)
        - Decision ID: {decision_pkg.get('id', 'N/A')}
        - Decision Package (JSON): 
        {decision_pkg_json}
        - User Confidence Score: {user_score:.2f}  (0.0 = bad, 1.0 = perfect)
        - User Note: "{user_note}"

        ---  
        ### ACTIVE RULES (CURRENT STATE)
        Analyze these rules carefully (Priority and Expires fields are important):
        {rules_text}

        ---  
        ### RULE HIERARCHY & EDITING RULES (STRICT)
        - Priority order (highest -> lowest): IMMEDIATE > MID_TERM > LONG_TERM.
        - To override an existing rule, the new rule MUST have strictly higher priority.
        - Prefer MODIFY (propose_modify_rule) when a change is a small adjustment; cite Rule ID.
        - Do NOT create two rules at the same priority that directly contradict each other.
        - Use ISO timestamps for temporary expires_at fields: YYYY-MM-DDTHH:MM:SSZ

        ---  
        ### REQUIRED WORKFLOW (FOLLOW EXACTLY)
        1. DIAGNOSE: Read the Decision Package + user feedback and identify the root cause (missing rule, wrong priority, overly broad rule, conflict, missing expiration, etc.). This content will become your `chain_of_thought`.
        2. DECIDE: For each necessary correction choose one of: CREATE, MODIFY, DELETE.
        3. ACT (MANDATORY): Invoke the appropriate tool for every change you propose:
        - propose_create_rule(rule_text, priority, expires_at)
        - propose_modify_rule(rule_id, rule_text, priority, expires_at)
        - propose_delete_rule(rule_id)
        The canonical output objects produced by the tools MUST appear in the `rule_proposals` array in the final JSON.
        4. RETURN: Output ONLY the RAW JSON object exactly matching the Mandatory Output Format block above.

        ---  
        ### FAILURE MODES & LOGGING
        - If you cannot identify a precise corrective action, still return a meaningful `chain_of_thought` explaining why and return `"rule_proposals": []`.
        - Do NOT return any additional guidance, checklist, or human-readable bullets outside the required JSON object.

        ---  
        Now proceed with the analysis, tool invocations as needed, and return ONLY the RAW JSON object as specified.
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
    
    input_text = "Analyze the context and generate rule proposals following the instructions and MANDATORY OUTPUT FORMAT."
    
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content=input_text),
    ])
    
    agent_chain = prompt_template | llm_with_tools

    try:
        # Aquí es donde el LLM ejecutará las herramientas (propose_create_rule, etc.)
        raw_output = await asyncio.to_thread(
            lambda: agent_chain.invoke({"input": input_text})
        )
        
        # El output contiene el JSON generado por el LLM, que incluye 'chain_of_thought' y 'rule_proposals'
        llm_response_text = raw_output.content
        
        # Intentamos parsear la respuesta final del LLM
        response_json = json.loads(llm_response_text)
        
        return {
            "chain_of_thought": response_json.get("chain_of_thought", "No COT provided."),
            "rule_proposals": response_json.get("rule_proposals", [])
        }
        
    except Exception as e:
        logger.exception("Error calling LLM for rule generation: %s", e)
        # Devolvemos un error estructurado para el frontend
        return {
            "chain_of_thought": f"ERROR: Falló la generación de reglas: {e}",
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