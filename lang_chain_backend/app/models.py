# app/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Any

class Observation(BaseModel):
    entity_id: str
    value: Any
    timestamp: Optional[str] = None

class SuggestedAction(BaseModel):
    action: str = Field(..., description="The Home Assistant service to call (e.g., turn_off, set_temperature).")
    target_entity: str = Field(..., description="The entity_id to target (e.g., climate.office_ac).")
    parameters: dict = Field(default={}, description="Key-value parameters for the service.")
    rationale: str = Field(..., description="Justification for this specific action.")


class DecisionPackage(BaseModel):
    chain_of_thought: str = Field(..., description="Step-by-step reasoning and rule citations justifying the decision. MUST BE PRESENT.")
    decision_type: str = Field(..., description="ACTION or NO_ACTION.")
    suggested_actions: List[SuggestedAction] = Field(default_factory=list, description="List of proposed actions.")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0).")
    goal: str = Field(..., description="Brief summary of the decision's objective.")


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
