from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field, ValidationError


class MutationProposal(BaseModel):
    mutation_id: Optional[str] = None
    agent_name: str
    description: str
    mutation_type: str = Field(pattern="^(code_change|config_change|prompt_change|tool_addition|strategy_evolution|parameter_adjustment)$")
    changes: Dict[str, Any] = Field(default_factory=dict)
    rationale: Optional[str] = None
    risk_level: str = Field(pattern="^(low|medium|high)$", default="medium")
    mission_pillar: Optional[int] = Field(default=None, ge=1, le=5)
    rollback_plan: Optional[str] = None
    proposed_changes: Optional[Dict[str, Any]] = None
    expected_improvement: Optional[float] = None


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


def validate_mutation_proposal(proposal: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        normalized = {
            "agent_name": proposal.get("agent_name", ""),
            "description": proposal.get("description", ""),
            "mutation_type": proposal.get("mutation_type", "parameter_adjustment"),
            "changes": proposal.get("proposed_changes") or proposal.get("changes") or {},
            "rationale": proposal.get("rationale"),
            "risk_level": proposal.get("risk_level", "medium"),
            "mission_pillar": proposal.get("mission_pillar"),
            "rollback_plan": proposal.get("rollback_plan"),
            "proposed_changes": proposal.get("proposed_changes"),
            "expected_improvement": proposal.get("expected_improvement"),
            "mutation_id": proposal.get("mutation_id"),
        }
        MutationProposal(**normalized)
        return True, "Valid Pydantic mutation proposal"
    except ValidationError as exc:
        return False, f"Invalid mutation proposal: {exc.errors()[0]['type']} - {exc.errors()[0]['msg']}"


def validate_council_message(message: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        CouncilMessage(**message)
        return True, "Valid council message"
    except ValidationError as exc:
        return False, f"Invalid council message: {exc.errors()[0]['type']} - {exc.errors()[0]['msg']}"
