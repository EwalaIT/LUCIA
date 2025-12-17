# services/agent_db_query.py
from __future__ import annotations

import logging
from typing import Optional, Any

from config import settings

# LangChain modern imports
try:
    from langchain_community.utilities import SQLDatabase
    from langchain_community.agent_toolkits import (
        SQLDatabaseToolkit,
        create_sql_agent,
    )
except Exception:
    raise ImportError(
        "Could not import SQLDatabase / SQLDatabaseToolkit / create_sql_agent from LangChain. "
        "Ensure you are using a compatible 1.x installation."
    )

# LLM typing import
try:
    from langchain_core.language_models import BaseLanguageModel
except ImportError:
    BaseLanguageModel = object  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


def _build_sqlite_uri(db_path: Optional[str]) -> str:
    """
    Helper to build a valid SQLite URI for LangChain SQLDatabase.
    """
    if not db_path:
        raise ValueError("Database path cannot be None or empty.")
    if not db_path.startswith("sqlite:///"):
        return f"sqlite:///{db_path}"
    return db_path


def create_db_query_agent(
    llm: BaseLanguageModel,
    db_path: Optional[str] = None,
    verbose: bool = False,
    max_iterations: int = 3,
) -> Any:
    """
    Create a runnable SQL agent chain (LCEL pattern) to handle natural-language DB queries.
    Compatible with LangChain 1.x (nuevo patrón create_sql_agent).
    """
    sqlite_uri = _build_sqlite_uri(db_path)
    logger.info("Creating SQLDatabase from URI: %s", sqlite_uri)

    try:
        db = SQLDatabase.from_uri(sqlite_uri)
    except Exception as e:
        logger.exception("Failed creating SQLDatabase: %s", e)
        raise

    logger.debug("SQLDatabase created. Initializing toolkit...")

    try:
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    except Exception as e:
        logger.exception("Failed creating SQLDatabaseToolkit: %s", e)
        raise

    logger.debug("SQLDatabaseToolkit ready. Creating SQL Agent (LCEL)...")

    try:
        agent = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=verbose,
            max_iterations=max_iterations,
        )
    except Exception as e:
        logger.exception("Failed creating SQL agent: %s", e)
        raise

    logger.info("✅ Agente DB Query (LCEL) creado correctamente.")
    return agent


def test_db_query_agent(agent: Any) -> str:
    """
    Run a simple test query against the DB agent using the new LCEL .invoke() pattern.
    """
    try:
        if hasattr(agent, "run"):
            return agent.run("SELECT name FROM sqlite_master WHERE type='table';")
        return "El agente no tiene método run()."
    except Exception as e:
        logger.exception("Error al probar el agente SQL: %s", e)
        return f"Error al probar el agente SQL: {e}"