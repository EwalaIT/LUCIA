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

    # 2) Safety check
    try:
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
        action_name = action.get("action") or action.get("service") or ""
        target = action.get("target_entity") or action.get("entity_id") or ""
        params = action.get("parameters") or {}

        try:
            if not target or "." not in target:
                raise ValueError(f"Invalid target_entity: {target}")

            domain = target.split(".", 1)[0]
            service = action_name

            if domain == "climate" and service == "set_temperature":
                if "value" in params:
                    params["temperature"] = params.pop("value")
                params["entity_id"] = target
                if "temperature" not in params and "target_temp" in action:
                    params["temperature"] = action["target_temp"]

            logger.info("Calling HA service %s.%s for %s params=%s", domain, service, target, params)
            res = ha.call_service(domain=domain, service=service, entity_id=target, data=params)

            action_results.append({
                "action": action,
                "result": res,
                "status": "OK"
            })
            logger.info("Action executed OK for decision %s: %s -> %s", decision_id, action, res)

        except Exception as e:
            logger.exception("Action execution failed for decision %s: %s", decision_id, e)
            action_results.append({
                "action": action,
                "result": str(e),
                "status": "FAILED"
            })
            overall_failed = True

    # 4) Persist execution results
    action_summary_list = []
    target_entities_list = []

    for a in action_results:
        action_dict = a.get("action", {})
        status = a.get("status", "FAILED")
        result = a.get("result") if status == "OK" else [a.get("result")]

        action_summary_list.append({
            "action_name": action_dict.get("action") or action_dict.get("service"),
            "target_entity": action_dict.get("target_entity") or action_dict.get("entity_id"),
            "parameters": action_dict.get("parameters") or {},
            "result": result,
            "status": status
        })

        target_entity = action_dict.get("target_entity") or action_dict.get("entity_id")
        if target_entity:
            target_entities_list.append(target_entity)

    try:
        action_summary_json = json.dumps(action_summary_list, ensure_ascii=False)
    except Exception:
        action_summary_json = str(action_summary_list)

    target_entity_str = ",".join(target_entities_list)
    action_result_status = "OK" if not overall_failed else "Error in one or more actions"
    executed_action_summary = "; ".join(
        [f'{a["action_name"]} on {a["target_entity"]}' for a in action_summary_list]
    )
    
    final_status = "FAILED" if overall_failed else "EXECUTED"

    update_decision_status(
        decision_id,
        final_status,
        action_summary=action_summary_json,
        executed_action=executed_action_summary,
        action_result=action_result_status,
        target_entity=target_entity_str
    )
    _schedule_broadcast(decision_id, final_status)

    return {
        "status": final_status,
        "actions": action_summary_list
    }