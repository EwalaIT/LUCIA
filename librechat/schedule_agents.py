#!/usr/bin/env python3
"""
LibreChat Agents Async Scheduler
--------------------------------
Ejecuta agentes de LibreChat periódicamente en paralelo,
registra logs diarios y permite ajuste dinámico del intervalo.
"""

import asyncio
import aiohttp
import logging
from logging.handlers import TimedRotatingFileHandler
from urllib.parse import urlparse
import os

# ==============================
# CONFIGURACIÓN
# ==============================

AGENTS = {
    "Monitor": "http://192.168.230.142:3090/c/new?agent_id=agent__vh5tknfrG4412wnEUuLP&submit=true",
    "Decision": "http://192.168.230.142:3090/c/new?agent_id=agent_Tu816baGxaNdrhVVoCJr9&submit=true"
}

INTERVAL = int(os.getenv("LIBRECHAT_INTERVAL", 5 * 60))  # segundos, configurable vía env
TIMEOUT = 15               # Timeout para cada petición
RETRY_DELAY = 10           # Retries en caso de fallo
MAX_RETRIES = 3

LOG_FILE = "/home/jetson/Downloads/LUCIA/logs/librechat_agents.log"

# ==============================
# LOGGING PROFESIONAL
# ==============================

logger = logging.getLogger("LibreChatScheduler")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

# Consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Rotación diaria de logs
file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=7)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ==============================
# FUNCIONES
# ==============================

def validate_url(url: str) -> bool:
    """Valida que la URL sea correcta."""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False

async def fetch_agent(session: aiohttp.ClientSession, name: str, url: str):
    """Ejecuta un agente con retries, timeout y logging."""
    if not validate_url(url):
        logger.error(f"{name} URL inválida: {url}")
        return None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(url, timeout=TIMEOUT) as response:
                response.raise_for_status()
                text = await response.text()
                logger.info(f"{name} ejecutado correctamente. Status code: {response.status}")
                return text
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"{name} fallo intento {attempt}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"Reintentando en {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error(f"{name} no pudo ejecutarse tras {MAX_RETRIES} intentos.")
    return None

async def run_agents():
    """Ejecuta todos los agentes en paralelo."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_agent(session, name, url) for name, url in AGENTS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for name, result in zip(AGENTS.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"{name} devolvió excepción: {result}")
            elif result is not None:
                logger.info(f"{name} output length: {len(result)} caracteres")
        logger.info("-" * 50)

async def scheduler():
    """Loop principal del scheduler."""
    logger.info("Inicio del scheduler asincrónico de agentes LibreChat.")
    while True:
        await run_agents()
        logger.info(f"Esperando {INTERVAL // 60} minutos para la próxima ejecución...\n")
        await asyncio.sleep(INTERVAL)

# ==============================
# EJECUCIÓN
# ==============================

if __name__ == "__main__":
    try:
        asyncio.run(scheduler())
    except KeyboardInterrupt:
        logger.info("Scheduler detenido por el usuario.")
    except Exception as e:
        logger.exception(f"Error inesperado: {e}")
