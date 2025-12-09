# app/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

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

class ChatRequest(BaseModel):
    instruction: str

class ToolCallContext(BaseModel):
    conversation_id: Optional[str] = Field(
        None, description="Unique conversation/session identifier."
    )
    user_id: Optional[str] = Field(
        None, description="Identifier of the user or client."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata sent by the MCP client."
    )


class AgentRequest(BaseModel):
    instruction: str = Field(..., description="User prompt or instruction.")
    tool_context: Optional[ToolCallContext] = Field(
        default=None, description="Metadata injected by FastMCP (conversation_id, user_id, etc.)."
    )


class AgentResponse(BaseModel):
    output: str = Field(..., description="Generated response from the agent.")
    finished: bool = Field(default=True, description="Indicates if the agent finished processing.")
    debug: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional debugging information (timings, metadata, raw outputs, etc.)."
    )
    
class DecisionPackageMCP(BaseModel):
    decision_type: str = Field(..., description="ACTION, NO_ACTION, or EVALUATE")
    reasoning: str = Field(..., description="Justificación detallada de la decisión")
    target_entity: Optional[str] = Field(None, description="Entidad objetivo para la acción")
    action_params: Optional[Dict[str, Any]] = Field(default=None, description="Parámetros de acción específicos")