# services/ha_tools.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

import requests
from pydantic import BaseModel, Field
from db.entities import get_selected_entity_ids
from langchain_core.tools import StructuredTool

from config import settings

logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level.upper())


class HomeAssistantAPI:
    """Synchronous wrapper for Home Assistant REST API using requests.Session."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        base = base_url or str(settings.ha_url)
        self.base_url = f"{base.rstrip('/')}/api"
        self.token = token or settings.ha_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        )
        logger.debug("HomeAssistantAPI initialized at %s", self.base_url)

    def get_state(self, entity_id: str, timeout: float = 10.0) -> Dict[str, Any]:
        """
        GET /api/states/{entity_id}
        Returns the parsed JSON body as dict.
        Raises requests.HTTPError on bad status.
        """
        url = f"{self.base_url}/states/{entity_id}"
        logger.debug("HA GET state: %s", url)
        resp = self.session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    
    def get_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene los estados de todas las entidades marcadas como 'selected=1' en la BBDD.
        Devuelve un mapeo {entity_id: HA_state_dict}.
        """
        # 1. Obtener IDs seleccionadas de la BBDD
        selected_ids: List[str] = get_selected_entity_ids()
        
        if not selected_ids:
            logger.warning("No entity IDs selected in the database. Returning empty state.")
            return {}
        
        full_state: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Fetching states for {len(selected_ids)} selected entities...")
        
        # 2. Iterar y obtener el estado individualmente
        for entity_id in selected_ids:
            state_data = self.get_state(entity_id)
            if state_data:
                # El formato de HA es un diccionario con 'entity_id', 'state', 'attributes', etc.
                full_state[entity_id] = state_data
                
        logger.info(f"Successfully fetched states for {len(full_state)} entities.")
        return full_state

    def call_service(self, domain: str, service: str, entity_id: str, data: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
        """
        POST /api/services/{domain}/{service}
        payload should contain { "entity_id": ... } plus optional data.
        Returns the parsed JSON body as dict.
        """
        url = f"{self.base_url}/services/{domain}/{service}"
        payload = {"entity_id": entity_id}
        if data:
            payload.update(data)
        logger.debug("HA POST service: %s payload=%s", url, payload)
        resp = self.session.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        # HA returns 200 with minimal body; return parsed JSON if present, else a summary
        try:
            return resp.json()
        except ValueError:
            return {"status_code": resp.status_code, "text": resp.text}


# -------------------------
# LangChain Tools (Structured)
# -------------------------

# 1) get_current_state_tool
def _get_current_state_fn(entity_id: str) -> str:
    """
    Tool: fetches entity state from HA and returns a human-readable string.
    """
    ha = HomeAssistantAPI()
    try:
        state_obj = ha.get_state(entity_id)
        state = state_obj.get("state")
        attrs = state_obj.get("attributes", {})
        # Minimal summarization
        short_attrs = {k: v for k, v in attrs.items() if k in ("unit_of_measurement", "device_class", "friendly_name")}
        return f"Entity '{entity_id}' state='{state}' attrs={short_attrs}"
    except requests.HTTPError as e:
        logger.warning("get_current_state HTTP error for %s: %s", entity_id, e)
        return f"ERROR: could not fetch state for {entity_id}: {e}"
    except Exception as e:
        logger.exception("Unexpected error in get_current_state for %s", entity_id)
        return f"ERROR: unexpected error fetching state for {entity_id}: {e}"


get_current_state_tool = StructuredTool.from_function(
    func=_get_current_state_fn,
    name="get_current_state",
    description="Get the current state and some metadata of a Home Assistant entity (e.g. sensor.temp_room). Input: entity_id (str).",
)


# 2) call_service_tool
class CallServiceInput(BaseModel):
    domain: str = Field(..., description="Home Assistant domain, e.g. light, switch")
    service: str = Field(..., description="Service name, e.g. turn_on, turn_off")
    entity_id: str = Field(..., description="Target entity_id, e.g. switch.attic_fan")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional service data/parameters")


def _call_service_fn(domain: str, service: str, entity_id: str, params: Optional[Dict[str, Any]] = None) -> str:
    ha = HomeAssistantAPI()
    try:
        resp = ha.call_service(domain=domain, service=service, entity_id=entity_id, data=params or {})
        return f"Service {domain}.{service} called for {entity_id}. Response: {resp}"
    except requests.HTTPError as e:
        logger.warning("call_service HTTP error %s.%s on %s: %s", domain, service, entity_id, e)
        return f"ERROR: service call failed: {e}"
    except Exception as e:
        logger.exception("Unexpected error in call_service for %s.%s on %s", domain, service, entity_id)
        return f"ERROR: unexpected error calling service: {e}"


call_service_tool = StructuredTool.from_function(
    func=_call_service_fn,
    name="call_service",
    description="Call a Home Assistant service. Input: domain, service, entity_id, params (optional).",
)


# 3) vlm_fetch_tool (simulated VLM)
class VLMFetchInput(BaseModel):
    camera_id: str = Field(..., description="Camera identifier or entity id")


def _vlm_fetch_fn(camera_id: str) -> str:
    """
    Simulated Visual Language Model (VLM) tool.
    In production you would fetch an image and run inference.
    For PoC we return a concise summary.
    """
    logger.info("VLM fetch simulated for camera_id=%s", camera_id)
    # Simulated deterministic message
    return "The image is clear. No people detected."


vlm_fetch_tool = StructuredTool.from_function(
    func=_vlm_fetch_fn,
    name="vlm_fetch",
    description="Simulated VLM: fetch image by camera_id and analyze (returns short summary).",
)


# 4) safety_check_tool (simulated)
class SafetyCheckInput(BaseModel):
    decision_json: str = Field(..., description="DecisionPackage JSON string to analyze for safety")


def safety_check_tool_func(decision_json: str) -> str:
    """
    Simulated safety check. Real implementation should validate actions,
    check blacklists, max power draw, schedules, etc.
    """
    logger.debug("Safety check invoked (simulated).")
    try:
        # quick parse to verify it's valid JSON
        _ = decision_json and decision_json.strip()
        return "Decision is safe to execute."
    except Exception as e:
        logger.exception("Safety check parsing failed")
        return f"Decision safety check failed: {e}"


safety_check_tool = StructuredTool.from_function(
    func=safety_check_tool_func,
    name="safety_check",
    description="Simulated safety analysis for a DecisionPackage JSON. Returns 'Decision is safe to execute.' or an error message.",
)