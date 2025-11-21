# app/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Any

class Observation(BaseModel):
    entity_id: str
    value: Any
    timestamp: Optional[str] = None


class SuggestedAction(BaseModel):
    action: str
    target_entity: str
    parameters: Optional[dict] = Field(default_factory=dict)
    rationale: Optional[str] = ""


class DecisionPackage(BaseModel):
    chain_of_thought: str
    suggested_actions: List[SuggestedAction]


class AgentLog(BaseModel):
    agent_name: str
    decision: str
    reasoning: str
    context: Optional[str] = ""
    timestamp: Optional[str] = None


class DecisorRequest(BaseModel):
    instruction: str


class QueryRequest(BaseModel):
    question: str


class AgentResponse(BaseModel):
    output: str
