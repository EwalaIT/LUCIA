# services/decision_executor.py
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from db.decisions import get_decision_by_id, update_decision_status, update_decision_execution
from services.ha_tools import HomeAssistantAPI, safety_check_tool_func

# broadcast function (async) provided by the websocket router; we will schedule it
try:
    from app.routers.websockets import broadcast_decision_update
except Exception:
    broadcast_decision_update = None  # optional; best-effort notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def async_execute_decision(decision_id: int, db_path: str, ha_api: HomeAssistantAPI) -> Dict[str, Any]:
    """Wrapper asíncrono para ejecutar decisiones sin bloquear el event loop."""
    return await asyncio.to_thread(execute_decision, decision_id, db_path)


def _is_safety_ok(safety_result: str) -> bool:
    """
    Heurística simple para interpretar el resultado de la comprobación de seguridad.
    Adáptalo si safety_check_tool_func devuelve estructura más rica.
    """
    if not safety_result:
        return False
    try:
        return "safe" in safety_result.lower() or "ok" in safety_result.lower()
    except Exception:
        return False


def _schedule_broadcast(decision_id: int, status: str) -> None:
    """
    Intenta agendar la coroutine broadcast_decision_update en el loop principal.
    Si no es posible, lo registra y continúa (no es crítico).
    """
    if broadcast_decision_update is None:
        logger.debug("broadcast_decision_update not available; skipping websocket notification.")
        return
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(broadcast_decision_update(decision_id, status), loop)
        except Exception:
            logger.exception("Failed to schedule websocket broadcast.")
    else:
        try:
            main_loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(broadcast_decision_update(decision_id, status), main_loop)
        except Exception:
            logger.debug("No running loop; websocket broadcast skipped.")


def execute_decision(decision_id: int, db_path: Optional[str] = None, ha_api: Optional[HomeAssistantAPI] = None) -> Dict[str, Any]:
    """
    Synchronous executor that:
      - loads decision (and parsed decision_package)
      - runs safety check
      - executes each suggested action via Home Assistant REST API
      - updates DB status and execution summary
    """
    logger.info("🔧 Executing decision id=%s", decision_id)

    # 1) Load decision
    row = get_decision_by_id(decision_id)
    if not row:
        logger.error("Decision id=%s not found.", decision_id)
        raise ValueError("Decision not found")

    # determine decision_package dict
    decision_pkg = row.get("decision_package")
    if decision_pkg is None:
        # maybe stored as raw JSON string under decision_package_json
        raw_json = row.get("decision_package_json")
        if raw_json:
            try:
                decision_pkg = json.loads(raw_json)
            except Exception:
                decision_pkg = {"raw": raw_json}
        else:
            update_decision_status(decision_id, "FAILED", action_summary="Missing decision_package")
            _schedule_broadcast(decision_id, "FAILED")
            return {"status": "FAILED", "reason": "Missing decision_package"}

    # 2) Safety check (executor level)
    try:
        # safety_check_tool_func expects a JSON string; pass serialized package
        safety_input = json.dumps(decision_pkg, ensure_ascii=False)
        safety_result = safety_check_tool_func(safety_input)
        logger.info("Safety check for decision %s -> %s", decision_id, safety_result)
    except Exception as e:
        logger.exception("Safety check failed: %s", e)
        update_decision_status(decision_id, "FAILED", action_summary=f"Safety check exception: {e}")
        _schedule_broadcast(decision_id, "FAILED")
        return {"status": "FAILED", "reason": f"Safety check exception: {e}"}

    if not _is_safety_ok(safety_result):
        logger.warning("Decision %s rejected by safety: %s", decision_id, safety_result)
        update_decision_status(decision_id, "REJECTED", action_summary=f"Safety failed: {safety_result}")
        _schedule_broadcast(decision_id, "REJECTED")
        return {"status": "REJECTED", "safety_result": safety_result}

    # 3) Execute suggested_actions
    actions = decision_pkg.get("suggested_actions", []) if isinstance(decision_pkg, dict) else []
    if not actions:
        update_decision_status(decision_id, "EXECUTED", action_summary="No suggested_actions")
        _schedule_broadcast(decision_id, "EXECUTED")
        return {"status": "EXECUTED", "actions": []}

    ha = ha_api or HomeAssistantAPI()
    action_results = []
    overall_failed = False

    for action in actions:
        try:
            # Normalize keys
            action_name = action.get("action") or action.get("service") or ""
            target = action.get("target_entity") or action.get("entity_id") or ""
            params = action.get("parameters") or {}

            if not target or "." not in target:
                raise ValueError(f"Invalid target_entity: {target}")

            domain = target.split(".", 1)[0]
            service = action_name
            # If service is like "set_temperature" and domain == "climate", HA expects service 'set_temperature'
            # We'll call with full payload.
            logger.info("Calling HA service %s.%s for %s params=%s", domain, service, target, params)
            res = ha.call_service(domain=domain, service=service, entity_id=target, data=params)
            action_results.append({"action": action, "result": res, "status": "OK"})
            logger.info("Action executed OK for decision %s: %s", decision_id, action)
        except Exception as e:
            logger.exception("Action execution failed for decision %s: %s", decision_id, e)
            action_results.append({"action": action, "error": str(e), "status": "FAILED"})
            overall_failed = True

    # 4) Persist execution results
    try:
        summary = json.dumps(action_results, ensure_ascii=False)
    except Exception:
        summary = str(action_results)

    executed_action_summary = "; ".join(
        [f"{a.get('action') or a.get('service')} on {a.get('target_entity') or a.get('entity_id')}" for a in actions]
    )

    if overall_failed:
        update_decision_status(decision_id, "FAILED", action_summary=summary, executed_action=executed_action_summary, action_result=summary)
        _schedule_broadcast(decision_id, "FAILED")
        return {"status": "FAILED", "actions": action_results}
    else:
        update_decision_status(decision_id, "EXECUTED", action_summary=summary, executed_action=executed_action_summary, action_result=summary)
        _schedule_broadcast(decision_id, "EXECUTED")
        return {"status": "EXECUTED", "actions": action_results}