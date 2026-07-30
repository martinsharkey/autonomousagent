from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MutationProposal(BaseModel):
    mutation_id: Optional[str] = None
    agent_name: str
    description: str
    mutation_type: str = Field(pattern="^(code_change|config_change|prompt_change|tool_addition|strategy_evolution)$")
    changes: Dict[str, Any]
    rationale: Optional[str] = None
    risk_level: str = Field(pattern="^(low|medium|high)$", default="medium")
    mission_pillar: Optional[int] = Field(default=None, ge=1, le=5)
    rollback_plan: Optional[str] = None


class CouncilVote(BaseModel):
    proposal_id: str
    agent_name: str
    vote: str = Field(pattern="^(approve|reject)$")
    reason: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CouncilMessage(BaseModel):
    speaker: str
    body: str
    parse_mode: str = Field(default="HTML", pattern="^(HTML|Markdown)$")
    chat_id: Optional[str] = None


class MutationNotification(BaseModel):
    mutation: MutationProposal
    votes: Dict[str, str] = {}
    status: str = Field(default="pending", pattern="^(pending|approved|rejected)$")
    implementation_result: Optional[Dict[str, Any]] = None
