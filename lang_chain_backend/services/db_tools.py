# services/db_tools.py
"""
Database access layer for the LangChain Agent backend.

- This module is the ONLY one that imports sqlite3.
- All functions are synchronous and safe to call from async code via:
    await asyncio.to_thread(func, ...)
- Provides DB helpers for:
    * Observations persistence
    * Decision (HITL) lifecycle
    * Prompts management
    * Contexts / memory entries
    * LangChain StructuredTools wrappers that call these sync functions
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from db.decisions import persist_new_decision
from db.prompts import get_active_prompts

from config import settings

DEFAULT_TIMEOUT = 30

logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level.upper())

# ---------------------------------------------------------------------------
# LangChain Structured Tools wrapping sync DB functions
# - insert_decision_tool: calls persist_new_decision
# - fetch_prompts_tool: calls get_active_prompts
# ---------------------------------------------------------------------------
class InsertDecisionInput(BaseModel):
    decision_package_json: str
    goal: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    action_summary: Optional[str] = None
    executed_action: Optional[str] = None
    target_entity: Optional[str] = None
    action_result: Optional[str] = None
    notes: Optional[str] = None


def insert_decision_tool_func(
    decision_package_json: str,
    goal: Optional[str] = None,
    reasoning: Optional[str] = None,
    confidence: Optional[float] = None,
    action_summary: Optional[str] = None,
    executed_action: Optional[str] = None,
    target_entity: Optional[str] = None,
    action_result: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Tool function used by LangChain to persist a decision.
    Returns a short confirmation string including the new decision id.
    """
    decision_id = persist_new_decision(
        decision_package_json=decision_package_json,
        goal=goal,
        reasoning=reasoning,
        confidence=confidence,
        status="PENDING",
        action_summary=action_summary,
        executed_action=executed_action,
        target_entity=target_entity,
        action_result=action_result,
        notes=notes,
    )
    return f"Decision persisted with id={decision_id}"


insert_decision_tool = StructuredTool.from_function(
    func=insert_decision_tool_func,
    name="insert_decision",
    description="Persist a DecisionPackage into the decisions table and return the new id.",
)


class FetchPromptsInput(BaseModel):
    dummy: str = Field("", description="Compatibility placeholder")


def fetch_prompts_tool_func(dummy: str = "") -> str:
    """
    Return the list of active prompts as a string (JSON serialized) for the LLM/tooling.
    """
    prompts = get_active_prompts()
    return json.dumps(prompts, ensure_ascii=False)


fetch_prompts_tool = StructuredTool.from_function(
    func=fetch_prompts_tool_func,
    name="fetch_prompts",
    description="Retrieve active prompts from the DB and return them as JSON string.",
)