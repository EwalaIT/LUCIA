from typing import List, Dict, Any, Optional
from datetime import datetime
from .connection import _get_conn
import json, logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompts management
# - get_active_prompts, update_prompt_content, set_prompt_status, 
# get_prompt_by_name, upsert_prompt
# ---------------------------------------------------------------------------
def get_active_prompts() -> List[Dict[str, Any]]:
    """
    Return a list of active prompts as dicts.
    Expected prompts table: id, name, content, status, last_modified
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, content, status, last_modified FROM prompts WHERE status = 'active';")
        rows = cur.fetchall()
        prompts = [dict(r) for r in rows]
        logger.debug(f"Fetched {len(prompts)} active prompts.")
        return prompts
    finally:
        conn.close()


def update_prompt_content(prompt_id: int, new_content: str) -> None:
    """
    Update prompt content and last_modified timestamp.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE prompts
            SET content = ?, last_modified = ?
            WHERE id = ?;
            """,
            (new_content, datetime.now().isoformat(), prompt_id),
        )
        conn.commit()
        logger.info(f"Prompt {prompt_id} content updated.")
    finally:
        conn.close()


def set_prompt_status(prompt_id: int, status: str) -> None:
    """
    Set prompt status to 'active' or 'inactive' (or any custom status).
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE prompts
            SET status = ?, last_modified = ?
            WHERE id = ?;
            """,
            (status, datetime.now().isoformat(), prompt_id),
        )
        conn.commit()
        logger.info(f"Prompt {prompt_id} status set to {status}.")
    finally:
        conn.close()
        
        
def get_prompt_by_name(prompt_name: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prompts WHERE name=?", (prompt_name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_prompt(prompt_name: str, content: str) -> int:
    """
    Inserta o actualiza un prompt en la tabla prompts.
    Si el prompt existe (name único), actualiza content y last_modified.
    Si no existe, lo inserta con status='active' por defecto.
    Devuelve el id del prompt insertado o actualizado.
    """
    conn = _get_conn()
    cursor = conn.cursor()
    try:
        # Intentar actualizar primero
        cursor.execute(
            "UPDATE prompts SET content=?, last_modified=? WHERE name=?",
            (content, datetime.utcnow().isoformat(), prompt_name),
        )
        if cursor.rowcount == 0:
            # No existía, insertar
            cursor.execute(
                "INSERT INTO prompts (name, content, status, last_modified) VALUES (?, ?, ?, ?)",
                (prompt_name, content, "active", datetime.utcnow().isoformat()),
            )
        conn.commit()
        # Obtener el id
        cursor.execute("SELECT id FROM prompts WHERE name=?", (prompt_name,))
        row = cursor.fetchone()
        prompt_id = row["id"] if row else -1
        return prompt_id
    finally:
        conn.close()