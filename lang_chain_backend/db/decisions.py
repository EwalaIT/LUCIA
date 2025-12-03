import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from .connection import _get_conn
import logging

logger = logging.getLogger(__name__)


# -----------------------
# Small validator for DecisionPackage structure
# -----------------------
def validate_decision_package(dp: Dict[str, Any]) -> bool:
    """
    Validates a minimal DecisionPackage shape. Raises ValueError on failure.
    Required structure (minimum):
      - chain_of_thought : str
      - suggested_actions: list[ { action, target_entity, parameters? , rationale? } ]
    Returns True if valid.
    """
    if not isinstance(dp, dict):
        raise ValueError("DecisionPackage must be an object.")

    if "chain_of_thought" not in dp or not isinstance(dp["chain_of_thought"], str):
        raise ValueError("Missing chain_of_thought (string).")

    if "suggested_actions" not in dp or not isinstance(dp["suggested_actions"], list):
        raise ValueError("Missing suggested_actions (list).")

    for idx, a in enumerate(dp["suggested_actions"]):
        if not isinstance(a, dict):
            raise ValueError(f"suggested_actions[{idx}] must be object.")
        if "action" not in a and "service" not in a:
            raise ValueError(f"suggested_actions[{idx}] missing 'action' or 'service'.")
        if "target_entity" not in a and "entity_id" not in a:
            raise ValueError(f"suggested_actions[{idx}] missing 'target_entity' or 'entity_id'.")
        
    return True


# ---------------------------------------------------------------------------
# Decision flow (HITL)
# - persist_new_decision
# - get_decision_by_id
# - update_decision_status
# ---------------------------------------------------------------------------
def persist_new_decision(
    decision_package_json: str,
    goal: Optional[str] = None,
    reasoning: Optional[str] = None,
    confidence: Optional[float] = None,
    status: str = "PENDING",
    action_summary: Optional[str] = None,
    executed_action: Optional[str] = None,
    target_entity: Optional[str] = None,
    action_result: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """
    Insert a new decision record into decisions table, returns decision_id.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        created_at = datetime.now().isoformat()

        cur.execute(
            """
            INSERT INTO decisions (
                goal, reasoning, decision_package_json, action_summary,
                status, executed_action, target_entity, action_result,
                confidence, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?); 
            """,
            (
                goal,
                reasoning,
                decision_package_json,
                action_summary,
                status,
                executed_action,
                target_entity,
                confidence,
                notes,
                created_at,
            ),
        )

        conn.commit()
        new_id = cur.lastrowid
        logger.info(f"🧠 New decision inserted id={new_id} status={status}")
        return new_id

    finally:
        conn.close()


def get_decision_by_id(decision_id: int) -> Optional[Dict[str, Any]]:
    """
        Retrieve a decision row by id as a dict, or None if not found.
        The returned dict includes a parsed 'decision_package' key (if JSON parseable).
    """
    conn = _get_conn()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM decisions WHERE id = ?;", (decision_id,))
        row = cur.fetchone()
        if not row:
            logger.debug(f"Decision id={decision_id} not found.")
            return None
        result = dict(row)

        # Parse decision_package_json into decision_package if possible
        pkg_json = result.get("decision_package_json")
        if pkg_json:
            try:
                result["decision_package"] = json.loads(pkg_json)
            except Exception:
                result["decision_package"] = pkg_json  # leave raw if cannot parse
        else:
            result["decision_package"] = None

        return result
    finally:
        conn.close()
        
        
def get_last_decision() -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recent decision row based on ID ordering.
    Automatically parses JSON fields.

    Returns:
        Optional[Dict[str, Any]]
    """
    conn = _get_conn()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        row = cur.execute("""
            SELECT * FROM decisions
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if not row:
            logger.info("[DB] No decisions found in the table.")
            return None

        result = dict(row)

        pkg_json = result.get("decision_package_json")
        if pkg_json:
            try:
                result["decision_package"] = json.loads(pkg_json)
            except json.JSONDecodeError:
                logger.warning("[DB] Invalid JSON in last decision. Leaving raw.")
                result["decision_package"] = pkg_json
        else:
            result["decision_package"] = None

        return result

    except Exception as e:
        logger.error(f"[DB] Error accessing last decision: {e}", exc_info=True)
        raise
    finally:
        conn.close()
        
        
def get_decisions_by_status(status: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve decisions filtered by status (PENDING, EXECUTED, FAILED, REJECTED, etc.)
    with optional limit. Uses whitelisting for SQL safety.

    Args:
        status (str): Decision status to filter.
        limit (int): Maximum number of records to return.

    Returns:
        List[Dict[str, Any]]: List of decisions.
    """
    ALLOWED_STATUSES = {"PENDING", "EXECUTED", "FAILED", "REJECTED"}
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Allowed: {ALLOWED_STATUSES}")

    conn = _get_conn()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM decisions WHERE status = ? ORDER BY id DESC LIMIT ?;",
            (status, limit),
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            r = dict(row)
            pkg_json = r.get("decision_package_json")
            if pkg_json:
                try:
                    r["decision_package"] = json.loads(pkg_json)
                except json.JSONDecodeError:
                    r["decision_package"] = pkg_json
            else:
                r["decision_package"] = None
            results.append(r)
        logger.info(f"[DB] Fetched {len(results)} decisions with status='{status}'")
        return results
    finally:
        conn.close()


def update_decision_status(
    decision_id: int,
    status: str,
    action_summary: Optional[str] = None,
    executed_action: Optional[str] = None,
    action_result: Optional[str] = None
):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE decisions
            SET 
                status = COALESCE(?, status),
                action_summary = COALESCE(?, action_summary),
                executed_action = COALESCE(?, executed_action),
                action_result = COALESCE(?, action_result)
            WHERE id = ?;
        """, (status, action_summary, executed_action, action_result, decision_id))
        conn.commit()
        logger.info(f"📝 Decision {decision_id} status updated -> {status}")
    finally:
        conn.close()

        
def update_decision_execution(decision_id: int, executed_action: str, action_result: str) -> None:
    """
    Convenience: set executed_action and action_result.
    """
    conn = _get_conn()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            UPDATE decisions
            SET executed_action = ?, action_result = ?
            WHERE id = ?;
        """, (executed_action, action_result, decision_id))
        conn.commit()
    finally:
        conn.close()
        
def update_decision_with_proposals(decision_id: int, proposals_json: str, chain_of_thought: str):
    """
    Updates a decision with the rule proposals and CoT generated by the Evaluator Agent.
    Sets the rule_status to 'RULES_READY'.
    """
    conn = _get_conn()
    cursor = conn.cursor()
    
    # 🚨 CAMBIO: Actualizamos rule_proposals_json, rule_cot, y rule_status
    cursor.execute("""
        UPDATE decisions 
        SET 
            rule_proposals_json = ?, 
            rule_cot = ?, 
            rule_status = 'RULES_READY' 
        WHERE id = ?
    """, (proposals_json, chain_of_thought, decision_id))
    
    conn.commit()
    conn.close()


def update_decision_rule_status(decision_id: int, rule_status: str):
    """
    Updates the rule processing status (NONE, IN_PROGRESS, RULES_READY, RULES_APPLIED).
    """
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE decisions SET rule_status = ? WHERE id = ?", (rule_status, decision_id))
    conn.commit()
    conn.close()