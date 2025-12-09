# services/db_tools.py
"""
Database access layer for the LangChain Agent backend.

- This module is the ONLY one that imports sqlite3.
- All functions are synchronous and safe to call from async code via:
    await asyncio.to_thread(func, ...)
- Provides DB helpers for:
    * Observations persistence
    * Decision (HITL) lifecycle
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

from config import settings

DEFAULT_TIMEOUT = 30

logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level.upper())

# ---------------------------------------------------------------------------
# LangChain Structured Tools wrapping sync DB functions
# - insert_decision_tool: calls persist_new_decision
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

def _create_rule_tool_func(rule_text: str, priority: str, expires_at: Optional[str] = None) -> str:
    return json.dumps({
        "action_type": "CREATE",
        "rule_text": rule_text,
        "priority": priority,
        "expires_at": expires_at
    })

create_rule_tool = StructuredTool.from_function(
    func=_create_rule_tool_func,
    name="propose_create_rule",
    description="Propose creating a new system rule based on evaluation. Parameters: rule_text (str), priority (immediate/mid_term/long_term), expires_at (Optional[str, ISO format]). Returns a JSON object describing the creation proposal."
)

def _modify_rule_tool_func(rule_id: int, new_rule_text: str, new_priority: str, new_expires_at: Optional[str] = None) -> str:
    return json.dumps({
        "action_type": "MODIFY",
        "rule_id": rule_id,
        "rule_text": new_rule_text,
        "priority": new_priority,
        "expires_at": new_expires_at
    })

modify_rule_tool = StructuredTool.from_function(
    func=_modify_rule_tool_func,
    name="propose_modify_rule",
    description="Propose modifying an existing system rule based on evaluation. Parameters: rule_id (int), new_rule_text (str), new_priority (str), new_expires_at (Optional[str, ISO format]). Returns a JSON object describing the modification proposal."
)


def _delete_rule_tool_func(rule_id: int) -> str:
    return json.dumps({
        "action_type": "DELETE",
        "rule_id": rule_id
    })
    
delete_rule_tool = StructuredTool.from_function(
    func=_delete_rule_tool_func,
    name="propose_delete_rule",
    description="Propose deleting an existing system rule based on evaluation. Parameter: rule_id (int). Returns a JSON object describing the deletion proposal."
)