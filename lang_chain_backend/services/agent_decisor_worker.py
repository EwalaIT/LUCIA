# services/agent_decisor_worker.py

import asyncio
import logging
from datetime import datetime
import json

from .agent_decisor import run_decisor
from db.decisions import persist_new_decision
from db.rules import get_formatted_rules_context
from config import settings
from services.ha_tools import HomeAssistantAPI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_decisor_task = None

from services.ha_tools import HomeAssistantAPI

async def _decision_loop(app):
    """
    Ejecuta el agente decisor en un bucle.
    Cada X segundos evalúa si debe tomar una decisión.
    """
    logger.info("🧠 Decision loop started.")

    exec_queue = app.state.exec_queue
    eval_queue = app.state.eval_queue

    ha_api = HomeAssistantAPI()
    ha_states = await ha_api.get_state()  # o fetch_ha_states()

    context = {e["entity_id"]: e["state"] for e in ha_states}
    try:
        while True:
            try:
                
                rules_context = get_formatted_rules_context()

                ha_states = await asyncio.to_thread(ha_api.get_state)
                context = {e["entity_id"]: e["state"] for e in ha_states}
                
                # 1) Ejecutar el ciclo del agente decisor
                result = await run_decisor(app, ha_instance="default", context=context, reason="periodic", rules_context=rules_context)

                if result is None:
                    await asyncio.sleep(settings.decisor_interval)
                    continue

                # Parsea el resultado del decisor (DecisionPackage)
                dp_json = json.dumps(result, ensure_ascii=False)

                # 2) Guardar en la tabla decisions
                decision_id = persist_new_decision(
                    decision_package_json=dp_json,
                    goal=result.get("goal"),
                    reasoning=result.get("reasoning"),
                    confidence=result.get("confidence"),
                    context_id=result.get("context_id"),
                    status="PENDING"
                )

                logger.info(f"💾 Decision registrada id={decision_id}")

                # 3) Enviar a la cola de ejecución
                await exec_queue.put({
                    "decision_id": decision_id,
                    "decision_package": result
                })

                logger.info(f"📤 Decision enviada a exec_queue id={decision_id}")

                # 4) Enviar a la cola de evaluación
                await eval_queue.put({
                    "prompt_name": "audit_decision",
                    "decision_id": decision_id,
                    "text": None
                })

                logger.info(f"📝 Decision enviada a eval_queue id={decision_id}")

            except Exception as e:
                logger.exception("❌ Error ejecutando decision cycle", e)

            await asyncio.sleep(settings.decisor_interval)

    except asyncio.CancelledError:
        logger.info("🧠 Decision loop cancelled.")


async def start_decision_loop(app):
    """
    Lanza el worker del decisor.
    """
    global _decisor_task

    if _decisor_task is None or _decisor_task.done():
        _decisor_task = asyncio.create_task(_decision_loop(app))
        logger.info("🧠 Decision worker started.")
    else:
        logger.warning("Decision worker already running.")


async def stop_decision_loop():
    global _decisor_task

    if _decisor_task and not _decisor_task.done():
        _decisor_task.cancel()
        try:
            await _decisor_task
        except asyncio.CancelledError:
            logger.info("Decision worker cancelled.")

    _decisor_task = None
