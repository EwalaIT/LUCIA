# services/observations_consumer.py
import asyncio
import logging
import json
from typing import Optional, Dict, Any

from fastapi import FastAPI

from app.models import Observation
from config import settings
from db.observations import persist_observation

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

# Global reference to the consumer task so we can cancel it in shutdown
_consumer_task: Optional[asyncio.Task] = None


async def observations_consumer_loop(app: FastAPI) -> None:
    """
    Loop principal del consumidor de observaciones.

    - Espera por items en app.state.observations_queue.
    - Por cada item llama a persist_observation en un hilo (asyncio.to_thread).
    - Llama a queue.task_done() siempre al terminar el procesamiento del item.
    """
    queue = getattr(app.state, "observations_queue", None)
    if queue is None:
        logger.error("Observations queue not found in app.state. Consumer will exit.")
        return

    logger.info("🟢 Observations consumer loop iniciado.")
    try:
        while True:
            obs_item = await queue.get()
            try:
                if isinstance(obs_item, Observation):
                    obs_dict = obs_item.model_dump()
                elif isinstance(obs_item, dict):
                    obs_dict = obs_item
                else:
                    try:
                        obs_dict = dict(obs_item)
                    except Exception:
                        obs_dict = {"raw": str(obs_item)}

                logger.debug("Procesando Observación (zona): %s", json.dumps(obs_dict, ensure_ascii=False))

                zone_id_str = obs_dict.get("entity_id", "")
                entities_data: Dict[str, Dict[str, Any]] = obs_dict.get("value", {})

                # Descomponer entities por device y guardar en DB
                for entity_id, entity_info in entities_data.items():
                    state = entity_info.get("state")
                    attributes = entity_info.get("attributes", {})
                    last_changed = entity_info.get("last_changed")

                    # Recuperar device_id desde attributes o tu mapeo interno
                    device_id = attributes.get("device_id") or attributes.get("parent_device_id")

                    # Construir registro para DB
                    persist_dict = {
                        "zone_id": zone_id_str.replace("zone.", ""),  # extraer id
                        "device_id": device_id,
                        "entity_id": entity_id,
                        "state": state,
                        "attributes": json.dumps(attributes, ensure_ascii=False),
                        "timestamp": last_changed,
                    }
                    
                    # Persistir en hilo separado
                    await asyncio.to_thread(persist_observation, persist_dict)

                logger.info("✅ Observación de zona procesada: %s", zone_id_str)

            except Exception as exc:
                logger.exception("Error procesando/persistiendo observación: %s", exc)
            finally:
                try:
                    queue.task_done()
                except Exception:
                    logger.debug("queue.task_done() falló o no soportado.")
    except asyncio.CancelledError:
        logger.info("🟡 Observations consumer detenido por cancelación.")
        raise
    except Exception as e:
        logger.exception("🔴 Observations consumer terminó inesperadamente: %s", e)
    finally:
        logger.info("Observations consumer loop finalizado.")


async def start_observations_consumer(app: FastAPI) -> None:
    """
    Inicia el worker consumidor como tarea de fondo.

    Uso: llamar desde @app.on_event("startup").
    """
    global _consumer_task
    if _consumer_task is None or _consumer_task.done():
        logger.info("Iniciando worker consumidor de observaciones...")
        _consumer_task = asyncio.create_task(observations_consumer_loop(app))
        # small delay allow task to start and potentially log errors early
        await asyncio.sleep(0)
        logger.info("🔵 Observations consumer started.")
    else:
        logger.debug("Observations consumer ya está corriendo.")


async def stop_observations_consumer(timeout: float = 10.0) -> None:
    """
    Solicita la cancelación del worker consumidor y espera su terminación.

    Uso: llamar desde @app.on_event("shutdown").
    """
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        logger.info("🟠 Requesting observations consumer cancellation...")
        _consumer_task.cancel()
        try:
            await asyncio.wait_for(_consumer_task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Observations consumer did not stop within timeout; cancelling forcefully.")
            try:
                _consumer_task.cancel()
            except Exception:
                pass
        except asyncio.CancelledError:
            logger.info("✅ Observations consumer stopped cleanly.")
        except Exception as exc:
            logger.exception("Error waiting for consumer to finish: %s", exc)
        finally:
            _consumer_task = None
            logger.info("🔴 Observations consumer task cleared.")
    else:
        logger.debug("Observations consumer task not running or already finished.")