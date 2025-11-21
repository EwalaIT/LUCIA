# services/agent_evaluator.py
from __future__ import annotations

import logging
import json
import asyncio
from typing import Optional
from config import settings

from langchain_ollama import OllamaLLM
from langchain_core.tools import StructuredTool
from db.prompts import upsert_prompt
from db.decisions import get_decision_by_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _build_evaluation_prompt(decision_pkg: dict) -> str:
    """
    Builds the system instruction for the automated Decision Package Auditor.
    This prompt instructs the LLM to analyze the DecisionPackage JSON for safety,
    clarity, and potential improvements.
    """
    return (
        "You are an automated Decision Package Auditor and Safety Guardrail. Your task is to perform a critical evaluation of the following proposed action plan.\n\n"
        "**Decision Package (JSON to Audit):**\n"
        f"{json.dumps(decision_pkg, indent=2, ensure_ascii=False)}\n\n"
        "**Evaluation Requirements:**\n"
        "Analyze the package based on the Chain of Thought and Suggested Actions. Provide a concise, professional audit summary using bullet points, covering all three mandatory criteria below:\n"
        " - **Safety Assessment:** Comment on potential risks or unintended consequences for devices/users. (e.g., 'Safe, as it only adjusts non-critical fan speed.')\n"
        " - **Clarity & Completeness:** Rate the clarity of the Chain of Thought and the completeness of the Suggested Actions (target_entity, parameters, rationale). (e.g., 'Clarity is good, but the 'parameters' field is missing the required fan mode.)\n"
        " - **Suggested Improvements:** Propose one or two specific, actionable improvements for better energy efficiency or logic optimization. (e.g., 'Improvement: Add a condition to check for user presence before turning off the light.')\n\n"
        "Return ONLY the audit summary (bullet points)."
    )


def _extract_llm_text(resp) -> str:
    """
    OllamaLLM sometimes returns a dict with .content, sometimes raw text.
    Normalize all possible formats.
    """
    try:
        # Response type 1: BaseMessage
        if hasattr(resp, "content"):
            return resp.content

        # Response type 2: dict from langchain
        if isinstance(resp, dict):
            if "content" in resp:
                return resp["content"]
            if "text" in resp:
                return resp["text"]
            return json.dumps(resp)

        # Response type 3: plain string
        return str(resp)

    except Exception:
        return str(resp)


def evaluate_and_update_prompt( prompt_name: str,
    decision_id: Optional[int] = None,
    text_override: Optional[str] = None
) -> dict:
    """
    Synchronous convenience function: load decision, call LLM to evaluate,
    and optionally upsert a prompt template with the evaluation.
    """
    if text_override:
        dp = {"manual_input": text_override}

    elif decision_id is not None:
        row = get_decision_by_id(decision_id)
        if not row:
            raise ValueError("Decision not found")

        dp_json = row.get("decision_package_json")
        try:
            dp = json.loads(dp_json)
        except Exception:
            dp = {"raw": dp_json}
    else:
        raise ValueError("Either decision_id or text_override must be provided")

    # 2) Construir prompt
    prompt = _build_evaluation_prompt(dp)

    # 3) Llamada al modelo Ollama
    llm = OllamaLLM(
        base_url=str(settings.ollama_url),
        model=settings.ollama_model,
        timeout=25
    )

    try:
        raw = llm.invoke(prompt)
        text = _extract_llm_text(raw)
    except Exception as e:
        logger.exception("Error calling LLM: %s", e)
        raise

    # 4) Guardar resultado en DB si se indicó nombre
    if prompt_name:
        upsert_prompt(prompt_name, text)

    return {
        "prompt_name": prompt_name,
        "decision_id": decision_id,
        "evaluation": text
    }


# StructuredTool for LangChain usage
def _update_prompt_tool_func(prompt_name: str, content: str) -> str:
    pid = upsert_prompt(prompt_name, content)
    return f"Prompt updated (id={pid})"


update_prompt_tool = StructuredTool.from_function(
    func=_update_prompt_tool_func,
    name="update_prompt_template",
    description="Upserts a prompt template into the prompt_templates table."
)

# -------------------------
# Worker asíncrono para evaluación en background
# -------------------------
_evaluator_task: Optional[asyncio.Task] = None


async def _evaluator_loop(app) -> None:
    """
    Bucle principal del worker que procesa la cola de decisiones para evaluar prompts.
    """
    queue: asyncio.Queue = app.state.eval_queue
    logger.info("Evaluator loop started.")

    try:
        while True:
            decision_item = await queue.get()
            try:
                result = await asyncio.to_thread(
                    evaluate_and_update_prompt,
                    decision_item.get("prompt_name"),
                    decision_item.get("decision_id"),
                    decision_item.get("text")
                )
                logger.info("Evaluator processed item: %s", result)
            except Exception as e:
                logger.exception("Error processing evaluation item: %s", e)
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