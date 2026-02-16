import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from .connection import _get_conn
import json, logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contexts / Memory entries (for db_memory adapter)
# - insert_context, get_contexts_by_type
# ---------------------------------------------------------------------------
def insert_memory_entry(session_id: str, input_text: str, output_text: str) -> int:
    """Inserta memoria en contexts como tipo 'mid_term'."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        payload = json.dumps(
            {"session": session_id, "input": input_text, "output": output_text},
            ensure_ascii=False
        )
        cur.execute(
            "INSERT INTO contexts (context_type, system_state, created_at) VALUES (?, ?, ?);",
            ("mid_term", payload, datetime.now().isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_memory_entries(session_id: str, limit: int = 10) -> List[dict]:
    """Obtiene las últimas entradas de memoria para una sesión dada."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, system_state, created_at FROM contexts WHERE context_type = ? ORDER BY created_at DESC LIMIT ?;",
            (session_id, limit),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_context(context_type: str, system_state: str) -> int:
    """
    Insert a context/memory entry into contexts table and return id.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        ts = datetime.now().isoformat()
        cur.execute(
            """
            INSERT INTO contexts (context_type, system_state, created_at)
            VALUES (?, ?, ?);
            """,
            (context_type, system_state, ts),
        )
        conn.commit()
        ctx_id = cur.lastrowid
        logger.info(f"Inserted context id={ctx_id} type={context_type}")
        return ctx_id
    finally:
        conn.close()
        

def get_context(context_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a context row by ID.

    Args:
        context_id (int): Context record ID.

    Returns:
        Optional[Dict[str, Any]]: Parsed context or None.
    """
    if not isinstance(context_id, int):
        raise TypeError("context_id must be an integer.")

    conn = _get_conn()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM contexts WHERE id = ?;", (context_id,))
        row = cur.fetchone()

        if not row:
            logger.info(f"[DB] Context id={context_id} not found.")
            return None

        result = dict(row)

        # Convert created_at into datetime if ISO
        created = result.get("created_at")
        if created:
            try:
                result["created_at"] = datetime.fromisoformat(created)
            except ValueError:
                logger.debug(f"[DB] Unparsable context timestamp id={context_id}. Keeping as string.")

        # Normalize system_state JSON (if you decide later to store JSON)
        state = result.get("system_state")
        if state and state.startswith("{") and state.endswith("}"):
            try:
                result["system_state"] = json.loads(state)
            except json.JSONDecodeError:
                logger.warning(f"[DB] Invalid JSON system_state in context id={context_id}.")

        return result

    except Exception as e:
        logger.error(f"[DB] Error retrieving context {context_id}: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def get_contexts_by_type(context_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve the last 'limit' contexts of a given type, ordered by created_at desc.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, context_type, system_state, created_at
            FROM contexts
            WHERE context_type = ?
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (context_type, limit),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
        
        
def get_context_for_decision(decision_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve the context associated with a specific decision_id.

    Args:
        decision_id (int): Decision ID.

    Returns:
        Optional[Dict[str, Any]]: Context row as dict, or None if not found.
    """
    if not isinstance(decision_id, int):
        raise TypeError("decision_id must be an integer")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.*
            FROM contexts c
            JOIN decisions d ON d.context_id = c.id
            WHERE d.id = ?;
            """,
            (decision_id,),
        )
        row = cur.fetchone()
        if not row:
            logger.info(f"[DB] No context found for decision_id={decision_id}")
            return None

        result = dict(row)
        # Parse system_state JSON
        state = result.get("system_state")
        if state and state.startswith("{") and state.endswith("}"):
            try:
                result["system_state"] = json.loads(state)
            except json.JSONDecodeError:
                logger.warning(f"[DB] Invalid JSON in system_state for context {result.get('id')}")
        # Parse created_at
        created = result.get("created_at")
        if created:
            try:
                result["created_at"] = datetime.fromisoformat(created)
            except ValueError:
                pass

        return result
    finally:
        conn.close()


def clear_memory_for_session(session_id: str) -> int:
    """
    Delete all memory entries for a given session_id from contexts.
    Returns the number of rows deleted.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM contexts WHERE context_type = ?;",
            (session_id,),
        )
        deleted = cur.rowcount
        conn.commit()
        logger.info(f"Cleared {deleted} memory entries for session {session_id}")
        return deleted
    finally:
        conn.close()
        

def purge_old_contexts(days: int = 90) -> int:
    """
    Delete context entries older than `days` days.
    
    Args:
        days (int): Number of days to keep; older entries are deleted.
    
    Returns:
        int: Number of rows deleted.
    """
    if days < 0:
        raise ValueError("days must be non-negative")

    cutoff_ts = datetime.now().timestamp() - (days * 86400)  # seconds
    cutoff_iso = datetime.fromtimestamp(cutoff_ts).isoformat()

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM contexts WHERE created_at < ?;", (cutoff_iso,))
        deleted = cur.rowcount
        conn.commit()
        logger.info(f"[DB] Purged {deleted} contexts older than {days} days")
        return deleted
    finally:
        conn.close()