# services/orchestrator.py
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI
from config import settings

from db.rules import get_formatted_rules_context
from services.ha_tools import HomeAssistantAPI
from services.agent_decisor import run_decisor
from services.decision_executor import async_execute_decision
from services.agent_evaluator import start_evaluator_loop
from services.db_memory import SQLiteMemoryAdapter
from services.monitor_worker import monitoring_loop

from db.decisions import persist_new_decision

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Orchestrator:
    """
    Orquestador completo:
    - Monitorea sensores
    - Construye contexto completo (snapshots + memoria histórica)
    - Ejecuta el decisor
    - Persiste y ejecuta decisiones
    - Evalúa decisiones y actualiza prompts/rediseños
    """

    def __init__(self, app: FastAPI, client):
        self.app = app
        self.client = client
        
        self._tasks: list[asyncio.Task] = []

        self.observations_queue: asyncio.Queue = getattr(app.state, "observations_queue", asyncio.Queue())
        self.exec_queue: asyncio.Queue = getattr(app.state, "exec_queue", asyncio.Queue())
        self.eval_queue: Optional[asyncio.Queue] = getattr(app.state, "eval_queue", None)

        self.decisor_interval = float(getattr(settings, "decisor_interval", 2.0))
        self.monitor_interval = float(getattr(settings, "monitor_interval_seconds", 5.0))

    async def start(self):
        logger.info("🚀 Starting Orchestrator workers...")

        # 1️⃣ Monitoring loop
        self._tasks.append(asyncio.create_task(monitoring_loop(self.app, self.client)))
        logger.info("🟢 Monitoring task scheduled.")

        # 2️⃣ Observations consumer loop
        self._tasks.append(asyncio.create_task(self._observations_loop()))
        logger.info("🟢 Observations loop scheduled.")

        # 3️⃣ Execution loop
        self._tasks.append(asyncio.create_task(self._execution_loop()))
        logger.info("🟢 Execution loop scheduled.")

        # 4️⃣ Evaluator loop
        if not getattr(self.app.state, "eval_queue", None):
            self.app.state.eval_queue = asyncio.Queue()
            logger.info("✅ Evaluator queue initialized in app.state.eval_queue.")
        # launch evaluator as background task
        self._tasks.append(asyncio.create_task(start_evaluator_loop(self.app)))
        logger.info("🟢 Evaluator task scheduled.")

        logger.info("✅ Orchestrator workers started.")

    async def stop(self):
        logger.info("🛑 Stopping Orchestrator...")
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("🛑 Orchestrator stopped.")

    async def _observations_loop(self):
        logger.info("🟢 Observations loop started.")
        while True:
            try:
                obs = await self.observations_queue.get()
                if obs is None:
                    await asyncio.sleep(self.decisor_interval)
                    continue
                await self._handle_observation(obs)
            except asyncio.CancelledError:
                logger.info("🟢 Observations loop cancelled.")
                break
            except Exception as e:
                logger.exception("❌ Error in observations loop: %s", e)
            await asyncio.sleep(self.decisor_interval)

    async def _handle_observation(self, observation: Dict[str, Any]):
        """
        Construye contexto completo + memoria histórica, ejecuta decisor, persiste decision,
        encola para ejecución y evaluación.
        """
        try:
            ha_instance = observation.get("ha_instance", "ha-primary")

            # 1) Crear contexto enriquecido: añadir memoria histórica
            memory = SQLiteMemoryAdapter(session_id=f"{ha_instance}_context")
            try:
                memory_vars = await asyncio.to_thread(memory.load_memory_variables, {})
                history_raw = memory_vars.get("history", [])
                history = [dict(row) if hasattr(row, 'keys') else row for row in history_raw]
            except Exception:
                logger.debug("No memory available or load failed; continuing without history.")
                history = []

            reason = observation.get("trigger_reason", "observation_update")
            
            ha_api = HomeAssistantAPI()
            ha_states = await asyncio.to_thread(ha_api.get_states)
            # 2) Ejecutar decisor (puede devolver id o package)
            rules_context = get_formatted_rules_context()
            
            full_context_for_decisor = {
                "current_state": ha_states, 
                "history": history 
            }
            
            logger.info("🧠 Running decisor for ha_instance=%s reason=%s", ha_instance, reason)
            decision_result = await run_decisor(self.app, ha_instance="default", context=full_context_for_decisor, reason=reason, rules_context=rules_context)

            # Si decisor no produjo nada, intentar fallback rule-based simple
            if not decision_result:
                logger.info("🔁 No DP from LLM; generating simple rule-based fallback decision.")
                decision_pkg = self._simple_rule_decision(full_context_for_decisor)
                # persist here
                decision_id = self._persist_decision_safe(decision_pkg)
                if decision_id is None:
                    logger.error("❌ Fallback decision could not be persisted.")
                    return
                decision_package = decision_pkg
            else:
                # run_decisor puede devolver {"decision_id", "decision_package"} o un decision_package directamente
                if isinstance(decision_result, dict) and "decision_id" in decision_result:
                    decision_id = decision_result.get("decision_id")
                    decision_package = decision_result.get("decision_package") or {}
                else:
                    # asumimos que es el decision_package
                    decision_package = decision_result
                    decision_id = self._persist_decision_safe(decision_package)
                    if decision_id is None:
                        logger.error("❌ Persist failed for DP returned by decisor.")
                        return

            # 4️⃣ Enqueue para ejecución
            await self.exec_queue.put({"decision_id": decision_id})
            logger.debug("📤 Decision enqueued for execution: %s", decision_id)

            # 5️⃣ Enqueue para evaluación
            eval_q = getattr(self.app.state, "eval_queue", None)
            if eval_q:
                await eval_q.put({"decision_id": decision_id, "prompt_name": f"auto_eval_{decision_id}"})
                logger.debug("📝 Decision enqueued for evaluation: %s", decision_id)

            # 6️⃣ Guardar en memoria histórica
            try:
                # Guardamos el estado completo actual asociado a esta decisión
                await asyncio.to_thread(
                    memory.save_context, 
                    {"observation": ha_states}, 
                    {"decision_id": decision_id, "goal": decision_package.get("goal")}
                )
            except Exception:
                logger.debug("No-op: memory.save_context failed (not fatal).")

        except Exception as exc:
            logger.exception("❌ Failed to handle observation: %s", exc)

    def _persist_decision_safe(self, decision_pkg: Dict[str, Any]) -> Optional[int]:
        """
        Intenta persistir usando persist_new_decision con distintas firmas posibles.
        Devuelve decision_id o None.
        """
        try:
            dp_json = json.dumps(decision_pkg, ensure_ascii=False)
        except Exception:
            dp_json = str(decision_pkg)

        # Intentar llamadas según distintas firmas posibles en db.decisions.persist_new_decision
        try:
            # signature antigua: (decision_package_json, agent_name, ...)
            decision_id = persist_new_decision(
                decision_package_json=dp_json,
                goal=decision_pkg.get("goal"),
                reasoning=decision_pkg.get("chain_of_thought") or decision_pkg.get("reasoning"),
                confidence=decision_pkg.get("confidence"),
                status="PENDING",
                action_summary=decision_pkg.get("action_summary"),
                executed_action=decision_pkg.get("executed_action"),
                target_entity=decision_pkg.get("target_entity"),
                action_result=decision_pkg.get("action_result"),
                notes=decision_pkg.get("notes"),
            )
            return decision_id
        except TypeError:
            # otra firma: (ha_instance=..., decision_package=...) from your older orchestrator attempt
            try:
                decision_id = persist_new_decision( decision_package=decision_pkg)
                return decision_id
            except Exception as e:
                logger.exception("Persist fallback failed: %s", e)
                return None
        except Exception as e:
            logger.exception("Persist failed: %s", e)
            return None

    def _simple_rule_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Regla mínima para generar una DecisionPackage:
        - si encuentra un sensor con 'temp' cuyo valor numérico > 25 -> turn_off ventilator (example).
        - si no, genera una decision noop con chain_of_thought vacía.
        """
        current = context.get("current_state", {})
        # current expected as mapping entity_id -> entity_info (state)
        suggested = []

        try:
            for ent_id, info in current.items():
                state = None
                if isinstance(info, dict):
                    state = info.get("state")
                else:
                    state = info
                # detect simple temperature
                if ent_id and "temp" in ent_id.lower():
                    try:
                        val = float(state)
                        if val > 25.0:
                            # action example: turn_off a fan or switch nearby
                            sug = {
                                "action": "turn_off",
                                "target_entity": ent_id.replace("sensor.", "switch.").replace("sensor_", "switch_"),
                                "parameters": {},
                                "rationale": f"Temperature {val} > 25°C observed on {ent_id}"
                            }
                            suggested.append(sug)
                    except Exception:
                        continue
        except Exception:
            suggested = []

        dp = {
            "chain_of_thought": "Fallback simple rule-based decision.",
            "suggested_actions": suggested or [],
            "confidence": 0.1,
            "decision_type": "fallback_rule"
        }
        return dp
    
    async def _execution_loop(self):
        logger.info("🟢 Execution loop started.")
        while True:
            try:
                item = await self.exec_queue.get()
                if item is None:
                    await asyncio.sleep(self.decisor_interval)
                    continue
                decision_id = item.get("decision_id")
                if decision_id is not None:
                    asyncio.create_task(async_execute_decision(decision_id=decision_id, db_path=str(settings.db_path), ha_api=None))
                    logger.debug("📤 Executing decision %s", decision_id)
            except asyncio.CancelledError:
                logger.info("🟢 Execution loop cancelled.")
                break
            except Exception as e:
                logger.exception("❌ Error in execution loop: %s", e)
            await asyncio.sleep(0.1)
