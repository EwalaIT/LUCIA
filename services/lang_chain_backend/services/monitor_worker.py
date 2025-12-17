# services/monitor_worker.py
import httpx
import asyncio
import logging
from typing import Any, Dict, Optional, List
from fastapi import FastAPI

from config import settings
from db.observations import get_selected_entities
from app.models import Observation
from services.ha_tools import HomeAssistantAPI

# Global state for hysteresis: store last known occupancy per zone
LAST_KNOWN_STATES: Dict[str, Optional[int]] = {}
MONITOR_TASK: Optional[asyncio.Task] = None

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


def _build_entity_map(data: List[dict], selected_only: bool = True) -> Dict[str, dict]:
    """
    Construye un dict rápido entity_id -> entity_data
    Si selected_only=True filtra solo entities seleccionadas.
    """
    if selected_only:
        return {e["entity_id"]: e for e in data if e.get("selected")}
    return {e["entity_id"]: e for e in data}


def _parse_numeric_state(val: Any) -> Optional[float]:
    """
    Intenta convertir el estado textual en número (float).
    Devuelve None si no es convertible.
    """
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _group_entities_by_zone(entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Agrupa entities por su zone_id."""
    zones_map: Dict[str, List[Dict[str, Any]]] = {}
    for ent in entities:
        zone_id = str(ent["zone_id"])
        zones_map.setdefault(zone_id, []).append(ent)
    return zones_map


async def post_observations(client: httpx.AsyncClient, observation: Observation, app=None) -> None:
    """
    POST aggregated Observation to the internal endpoint (http://localhost:8000/api/observations).
    Uses the provided AsyncClient for connection reuse.
    """
    payload = {
        "entity_id": observation.entity_id,
        "value": observation.value,
        "timestamp": observation.timestamp,
        # puedes añadir ha_instance u otros metadatos si los tienes
    }

    # Prefer queue if present (fast, local)
    try:
        if app is not None and hasattr(app.state, "observations_queue"):
            await app.state.observations_queue.put(payload)
            logger.debug("Observation enqueued into app.state.observations_queue: %s", observation.entity_id)
            return
    except Exception:
        logger.exception("Failed to enqueue observation to app.state.observations_queue; will fallback to HTTP POST.")

    url = "http://localhost:8000/api/observations"
    try:
        r = await client.post(url, json=payload, timeout=10.0)
        r.raise_for_status()
        logger.info("✅ Observation posted successfully (zone=%s). Status: %s", observation.entity_id, r.status_code)
    except Exception as e:
        logger.exception("Error posting observation via HTTP fallback: %s", e)


async def fetch_ha_states(ha_api: HomeAssistantAPI) -> Dict[str, Dict[str, Any]]:
    """
    Fetch all entity states from HA using HomeAssistantAPI.
    Retorna lista de dicts (cada dict = entity state).
    """
    try:
        resp = await asyncio.to_thread(ha_api.session.get, f"{ha_api.base_url}/states")
        resp.raise_for_status()
        return resp.json()  # retorna lista de dicts directamente
    except Exception as e:
        logger.exception("Error obteniendo estados de HA: %s", e)
        return []


async def monitoring_loop(app: FastAPI, client: httpx.AsyncClient) -> None:
    """
    Loop principal adaptado a:
    - Solo entities seleccionadas
    - Devices y zones asociados
    - Publica un Observation JSON por zona
    """
    logger.info("🚀 MonitorWorker iniciado.")
    ha_api = HomeAssistantAPI()

    try:
        while True:
            try:
                # 1️⃣ Obtener entities seleccionadas de la DB
                selected_entities = get_selected_entities()
                if not selected_entities:
                    logger.warning("No hay entities seleccionadas en la DB.")
                    await asyncio.sleep(settings.monitor_interval_seconds)
                    continue
                zones_map = _group_entities_by_zone(selected_entities)

                # 2️⃣ Obtener estados en tiempo real de HA
                ha_states_raw = await fetch_ha_states(ha_api)
                # Asegurarse de que ha_states_raw es lista de dicts
                if isinstance(ha_states_raw, dict):
                    ha_states_raw = list(ha_states_raw.values())

                ha_states: Dict[str, dict] = {
                    e.get("entity_id"): e for e in ha_states_raw if isinstance(e, dict) and "entity_id" in e
                }

                # 3️⃣ Iterar por zonas
                for zone_id, ent_list in zones_map.items():
                    aggregated: Dict[str, Any] = {}
                    count_val: Optional[int] = None
                    timestamp: Optional[str] = None

                    for ent in ent_list:
                        entity_id = ent["entity_id"]
                        entity_info = ha_states.get(entity_id)
                        if not entity_info:
                            logger.warning("Entity %s no encontrada en HA.", entity_id)
                            aggregated[entity_id] = None
                            continue
                        
                        state_val = entity_info.get("state")
                        aggregated[entity_id] = entity_info  # Guarda todo el dict

                        # Detectar occupancy_count si existe
                        if "count" in entity_id:
                            count_val = _parse_numeric_state(state_val)
                            if timestamp is None:
                                timestamp = entity_info.get("last_changed")

                        # fallback timestamp si no hay entity con count
                        if timestamp is None and "last_changed" in entity_info:
                            timestamp = entity_info["last_changed"]

                    # Hysteresis sobre occupancy_count
                    last_occ = LAST_KNOWN_STATES.get(zone_id)
                    should_emit = True
                    if count_val is not None:
                        should_emit = last_occ is None or abs(count_val - last_occ) >= 1
                        if should_emit:
                            LAST_KNOWN_STATES[zone_id] = count_val

                    # Emitir la observación
                    if should_emit:
                        observation = Observation(
                            entity_id=f"zone.{zone_id}",
                            value=aggregated,
                            timestamp=timestamp,
                        )
                        await post_observations(client, observation, app=app)
                    else:
                        logger.debug(
                            "Zona %s: occupancy no cambió significativamente (%s -> %s).",
                            zone_id, last_occ, count_val
                        )
            except asyncio.CancelledError:
                logger.warning("🛑 MonitorWorker cancelado (shutdown).")
                raise
            except Exception as e:
                logger.exception("Excepción inesperada en MonitorWorker: %s", e)

            # Sleep until next poll
            await asyncio.sleep(settings.monitor_interval_seconds)

    finally:
        logger.info("MonitorWorker finalizado.")


def start_monitoring_loop(app: FastAPI, client: httpx.AsyncClient
) -> None:
    """
    Lanza la tarea asíncrona que ejecuta monitoring_loop.
    Debe recibir el AsyncClient compartido (creado en app.startup) para reutilizar conexiones.
    """
    global MONITOR_TASK
    if client is None:
        raise ValueError("start_monitoring_loop requires a httpx.AsyncClient instance (client)")

    if MONITOR_TASK is None or MONITOR_TASK.done():
        MONITOR_TASK = asyncio.create_task(monitoring_loop(app, client))
        logger.info("🟢 Monitor task started.")
        

async def stop_monitoring_loop() -> None:
    """
    Cancela la tarea del monitor (graceful shutdown).
    """
    global MONITOR_TASK
    if MONITOR_TASK and not MONITOR_TASK.done():
        logger.info("🟠 Requesting Monitor task cancellation...")
        MONITOR_TASK.cancel()
        try:
            await MONITOR_TASK
        except asyncio.CancelledError:
            logger.info("✅ Monitor task stopped cleanly.")
        except Exception:
            logger.exception("❌ Error while waiting for Monitor task to finish.")
    else:
        logger.debug("Monitor task not running or already finished.")