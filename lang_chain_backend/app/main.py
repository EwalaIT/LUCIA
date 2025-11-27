# app/main.py
import os
import logging
import asyncio
from typing import Dict, Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from db.mcp_memory import init_db as mcp_init_db

from config import settings

# LLM wrappers
from langchain_ollama import ChatOllama

# Agents / workers
from services.agent_decisor import create_decisor_agent
from services.agent_db_query import create_db_query_agent
from services.orchestrator import Orchestrator

# Routers
from app.routers import agent_decisor, agent_db_query, execution, observations, websockets

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("app.main")

# ---------------------------
# FastAPI Initialization
# ---------------------------
app = FastAPI(title="LangChain Agent Backend", version="3.0")

# Optional: CORS for frontend local/dev (restrict in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Startup Event: Singleton Setup
# ---------------------------
@app.on_event("startup")
async def startup_event():
    """
    Initialize DB, LLM, agents, shared HTTP client, queues and start background workers.
    """
    logger.info("🚀 Starting backend...")

    # 0) Ensure DB schema is present from db/tables/*.sql (synchronous, run in thread)
    try:
        await asyncio.to_thread(mcp_init_db)
        logger.info("✅ DB initialized from db/mcp_memory SQL files (mcp_init_db).")
    except Exception:
        logger.exception("❌ Database initialization (mcp_init_db) failed. Aborting startup.")
        raise

    # 1) Shared Async HTTP client for workers / internal calls
    async_client = httpx.AsyncClient(timeout=15.0)
    app.state.httpx_client = async_client
    logger.info("✅ Shared AsyncClient created (timeout=15s).")

    # 2) Observations queue to decouple ingestion from persistence
    app.state.observations_queue = asyncio.Queue()
    logger.info("✅ Observations queue initialized (app.state.observations_queue).")

    # Execution queue for orchestrator -> executor
    app.state.exec_queue = asyncio.Queue()
    logger.info("✅ Execution queue initialized (app.state.exec_queue).")
    
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if getattr(settings, "langsmith_project", None):
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if getattr(settings, "langsmith_endpoint", None):
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    logger.info("✅ LangSmith observability activated (tracing v2).")
    
    # 3) Initialize LLM with fallback strategy
    llm = None    
    try:
        logger.info("Initializing Ollama LLM (primary)...")
        # Some Ollama wrappers accept base_url/model; adapt to your installed package
        llm = ChatOllama(base_url=str(settings.ollama_url), model=settings.ollama_model, timeout=15, format="json",)
        logger.info("✅ Ollama LLM initialized successfully.")
        if not hasattr(llm, 'bind_tools'):
         logger.error("ChatOllama no tiene 'bind_tools'. Por favor, actualiza langchain-core/langchain-community.")
         raise Exception("LLM class incompatible.")
    except Exception as exc:
        logger.exception("❌ CRITICAL: Ollama initialization failed. Aborting startup.")
        # Cerrar cliente antes de relanzar si falla todo
        await async_client.aclose() 
        raise # Detener el startup si el LLM principal falla

    # 4) Create singleton agent executors (synchronous construction expected)
    try:
        decisor_agent = create_decisor_agent(llm=llm)
        db_query_agent = create_db_query_agent(llm=llm, db_path=str(settings.db_path))

        app.state.agents = {
            "llm": llm,
            "decisor": decisor_agent,
            "db_query": db_query_agent,
        }
        logger.info("✅ Singleton agents ready and stored in app.state.agents.")
    except Exception as e:
        logger.exception("❌ Error creating agents: %s", e)
        # cleanup
        try:
            await async_client.aclose()
        except Exception:
            logger.debug("Error closing AsyncClient during agent creation failure.")
        raise
    
    # Crear orquestador
    orchestrator = Orchestrator(app, async_client)
    app.state.orchestrator = orchestrator
    try:
        await orchestrator.start()
    except Exception:
        logger.exception("❌ Orchestrator startup failed.")
        await async_client.aclose()
        raise

    logger.info("🚀 Startup complete.")


# ---------------------------
# Shutdown Event: Graceful cleanup
# ---------------------------
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🧹 Shutting down backend. Cleaning resources...")        
        
    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator:
        try:
            await orchestrator.stop()
            logger.info("✅ Orchestrator stopped.")
        except Exception:
            logger.exception("❌ Error stopping orchestrator.")


    # 4) Close shared AsyncClient
    client: Optional[httpx.AsyncClient] = getattr(app.state, "httpx_client", None)
    if client:
        try:
            await client.aclose()
            logger.info("✅ Shared AsyncClient closed.")
        except Exception:
            logger.exception("Error closing AsyncClient.")

    # 5) Clear agents
    if hasattr(app.state, "agents"):
        app.state.agents.clear()
        logger.info("✅ Agents cleared from app.state.")

    logger.info("✅ Shutdown complete.")


# ---------------------------
# Routers
# ---------------------------
app.include_router(observations.router, prefix="/api", tags=["Observations"])
app.include_router(agent_decisor.router, prefix="/agents/decisor", tags=["Decisor Agent"])
app.include_router(agent_db_query.router, prefix="/agents/db", tags=["DB Query Agent"])
app.include_router(execution.router, prefix="/api/decisions", tags=["Execution"])
app.include_router(websockets.router, tags=["WebSockets"])

# ---------------------------
# Health Check
# ---------------------------
@app.get("/health")
async def health():
    ok = hasattr(app.state, "agents") and "decisor" in app.state.agents
    queue_len = getattr(app.state, "observations_queue", None)
    qsize = queue_len.qsize() if queue_len else None
    return {"status": "ok" if ok else "degraded", "observations_queue_size": qsize}


# ---------------------------
# Run Server (Development)
# ---------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(settings.env == "development"),
    )