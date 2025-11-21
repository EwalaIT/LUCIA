import json
from datetime import datetime
from .connection import _get_conn
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Observations (ha_sensor_history)
# - persist_observation: insert aggregated Observation objects
# ---------------------------------------------------------------------------
def persist_observation(observation: Dict[str, Any]) -> int:
    """
    Persist an aggregated observation (dict with keys: entity_id, value (JSON-able), timestamp).
    Returns the inserted row id.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # Serialize value to JSON text
        entity_id = observation.get("entity_id")
        state = observation.get("state")
        timestamp = observation.get("timestamp")
        attributes_json = observation.get("attributes")
        cur.execute(
            """
            INSERT INTO ha_sensor_history (entity_id, current_value, timestamp, attributes)
            VALUES (?, ?, ?, ?);
            """,
            (entity_id, state, timestamp, attributes_json),
        )
        conn.commit()
        rowid = cur.lastrowid
        return rowid
    finally:
        conn.close()

# -------------------------------
# Queries dinámicas para observabilidad
# -------------------------------

def get_selected_entities() -> List[Dict]:
    """
    Retorna todas las entities seleccionadas (selected=1) junto con su device_id y zone_id.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT e.entity_id, e.device_id, d.zone_id, e.friendly_name, e.unit, e.mode
            FROM entity e
            JOIN device d ON e.device_id = d.id
            WHERE e.selected = 1;
            """
        )
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "entity_id": row[0],
                "device_id": row[1],
                "zone_id": row[2],
                "friendly_name": row[3],
                "unit": row[4],
                "mode": row[5],
            })
        return result
    finally:
        conn.close()


def get_devices_by_zone(zone_id: int) -> List[Dict]:
    """
    Retorna todos los devices de una zona.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, ha_device_id, name, type FROM device WHERE zone_id = ?", (zone_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "ha_device_id": r[1], "name": r[2], "type": r[3]} for r in rows]
    finally:
        conn.close()


def get_zone(zone_id: int) -> Optional[Dict]:
    """
    Retorna la información de una zona por id.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, description FROM zones WHERE id = ?", (zone_id,))
        row = cur.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "description": row[2]}
        return None
    finally:
        conn.close()