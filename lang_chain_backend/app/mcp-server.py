from fastmcp import FastMCP
from fastapi import FastAPI
from app.main import app as fast_api_app
import uvicorn
import logging
import asyncio
from typing import Dict, Any
from config import settings

# LLM wrappers
from langchain_ollama import ChatOllama

from services.agent_chat_commander import create_chat_commander_agent, run_chat_commander

logger = logging.getLogger("mcp-server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def init_mcp_agents(app_instance: FastAPI):
    """
    Inicializa el LLM y el agente chat_commander directamente para el MCP,
    guardándolos en app_instance.state.agents.
    """
    logger.info("Starting isolated LLM and Agent initialization for FastMCP...")

    # 0. Inicializar el diccionario de estado si no existe
    if not hasattr(app_instance.state, 'agents'):
        app_instance.state.agents: Dict[str, Any] = {}
        logger.info("App state for agents initialized.")

    # 1. Inicializar LLM (Mismo proceso que en app/main.py)
    llm = None
    try:
        logger.info("Initializing Ollama LLM...")
        llm = ChatOllama(
            base_url=str(settings.ollama_url),
            model=settings.ollama_model,
            timeout=15,
            format="json",
        )
        # Guardar LLM en el estado por si otros agentes lo necesitan
        logger.info("✅ Ollama LLM initialized successfully.")
    except Exception as exc:
        logger.exception("❌ CRITICAL: Ollama initialization failed. Aborting startup.")
        raise # Abortar si el LLM falla

    # 2. Crear el agente Chat Commander
    try:
        chat_commander = create_chat_commander_agent(llm)
        app_instance.state.agents["chat_commander"] = chat_commander
        logger.info("✅ Chat Commander agent created and stored in app.state.agents.")
    except Exception as e:
        logger.exception("❌ Error creating Chat Commander agent: %s", e)
        raise
# ---------------------------
# Initialize FastMCP
# ---------------------------
mcp = FastMCP(name="BuildingCommanderAgent")

@mcp.tool(name="chat", description=(
        "Use this tool to process a user's instruction and propose a building automation rule. "
        "The tool will decide whether to create, modify, or do nothing with existing rules. "
        "It must respect rule priorities (IMMEDIATE > MID_TERM > LONG_TERM) and safety constraints. "
        "Return a structured JSON with 'rule_text', 'priority', 'expires_at', and 'energy_impact'. "
        "Additionally, generate a short natural language summary for the user describing the action taken "
        "or the rule created."
    ))
async def chat_tool(instruction: str) -> str:
    """
    This tool forwards the instruction to your existing run_chat_commander logic.
    Returns the result dict.
    """
    # Nota: adapt as needed si tu función espera otros parámetros, contexto, etc.
    # Si necesitas acceso a toda la app, podrías inyectarla globalmente o usar otros mecanismos.
    result = await run_chat_commander(fast_api_app, instruction)
    return result


mcp_asgi = mcp.http_app(path="/mcp")

# ---------------------------
# Main entrypoint
# ---------------------------
if __name__ == "__main__":
    # 1. Ejecutar la inicialización asíncrona (LLM y Agentes) de forma aislada
    try:
        logger.info("Starting asynchronous initialization...")
        # Llama a la función asíncrona usando asyncio.run()
        asyncio.run(init_mcp_agents(fast_api_app)) 
        logger.info("✅ Initialization complete.")
    except Exception:
        logger.error("Failed to initialize agents. Aborting startup.")
        # Terminar el programa si la inicialización falla
        exit(1) 

    # 2. Iniciar el servidor FastMCP de forma síncrona utilizando uvicorn.
    # Esto evita el RuntimeError de anidación de bucles de eventos.
    port = 8001
    logger.info(f"🚀 Starting FastMCP server on 0.0.0.0:{port} (Uvicorn/ASGI)...")
    
    uvicorn.run(
        mcp_asgi, # Aplicación ASGI generada por FastMCP
        host="0.0.0.0",
        port=port,
        log_config=None, # Uvicorn usará nuestra configuración básica de logging
    )