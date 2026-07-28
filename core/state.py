from typing import TypedDict, Annotated, List, Dict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    loop_count: int
    recent_tool_invocations: Annotated[list[str], operator.add]
    completed_nodes: Annotated[list[str], operator.add]
    codebase_hash: str
    reasoning_traces: Annotated[list[str], operator.add]
    error_feedback: Annotated[list[dict], operator.add]
    last_error_trace: Optional[str]
    
    active_mutation_id: Optional[str]
    proposed_mutation_code: Optional[str]
    mission_rationale: Optional[str]
    council_votes: Dict[str, Optional[bool]]
    mission_scores: Dict[str, float]
    
    operator_override: Optional[str]
    operator_override_rationale: Optional[str]
    operator_override_timestamp: Optional[str]
    
    escalation_reason: Optional[str]
    requires_operator_approval: bool
    
    proposed_version: Optional[str]
    current_version: str
    
    rollback_pending: bool
    rollback_target_version: Optional[str]
    rollback_approved: bool
    rollback_reason: Optional[str]
