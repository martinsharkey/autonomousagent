import os
import json
import asyncio
from datetime import datetime
from core.api_router import get_llm_router
from core.state import AgentState
from core.models import get_primary_model, get_fallback_model
from core.agent_config import get_config_store
from governance.decision_logger import DecisionLogger
from governance.consensus import ConsensusEngine

MODEL_NAME = get_primary_model("alpha_evaluator")
FALLBACK_MODEL = get_fallback_model("alpha_evaluator")

# Initialize cloud router
llm_router = get_llm_router()
print(f"[ALPHA] Cloud-first LLM router initialized")

decision_logger = DecisionLogger()
consensus_engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
config_store = get_config_store()


def _load_active_config(agent_name: str):
    """Load current active config for mid-session config reloading."""
    try:
        config = config_store.get_active(agent_name)
        return config
    except Exception:
        return {}


async def _invoke_cloud(messages, temperature=0.1):
    """Invoke LLM through cloud router."""
    try:
        response = await llm_router.route_request(
            messages=messages,
            temperature=temperature
        )
        # Extract content from response
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        return type('Response', (), {'content': content})()
    except Exception as e:
        print(f"[ALPHA] Cloud router failed: {e}")
        raise

def alpha_node(state: AgentState):
    print(f"\n--- [ALPHA] Mission Alignment & Test Readiness Vote (Loop: {state['loop_count']}) ---")
    
    # Load active config (mid-session reload)
    config = _load_active_config("alpha_evaluator")
    temperature = config.get("temperature", 0.1)
    system_prompt = config.get("system_prompt", "You are Alpha, the mission alignment evaluator.")
    
    if state.get("active_mutation_id") and state.get("proposed_mutation_code"):
        proposal_text = state["proposed_mutation_code"]
        mission_rationale = state.get("mission_rationale", "No mission rationale provided")
        
        prompt = f"""
        You are Alpha, the mission alignment evaluator for the autonomous council.
        
        Evaluate this code mutation on two criteria:
        
        1. MISSION ALIGNMENT: Does this mutation serve the core mission?
        2. TEST READINESS: Is this mutation ready for testing?
        
        CORE MISSION:
        Autonomous 3-agent council with layered governance, zero-cost operation, 
        and safe self-evolution capabilities.
        
        MUTATION RATIONALE:
        {mission_rationale}
        
        PROPOSED MUTATION:
        {proposal_text}
        
        Respond with JSON:
        {{
            "vote": "APPROVE" or "REJECT",
            "confidence": 0.0-1.0,
            "mission_alignment": 0.0-1.0,
            "test_readiness": 0.0-1.0,
            "reasoning": "Your evaluation..."
        }}
        """
        
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        
        # Use cloud router
        response = asyncio.run(_invoke_cloud(messages, temperature))
        
        try:
            decision = json.loads(response.content)
            vote = decision.get("vote") == "APPROVE"
            confidence = decision.get("confidence", 0.5)
            reasoning = decision.get("reasoning", "No reasoning provided")
        except json.JSONDecodeError:
            vote = False
            confidence = 0.0
            reasoning = f"Failed to parse response: {response.content}"
        
        consensus_engine.cast_vote(
            proposal_id=state["active_mutation_id"],
            agent_name="alpha_evaluator",
            vote="approve" if vote else "reject",
            reason=reasoning
        )
        
        decision_logger.log(
            decision_type="MISSION_ALIGNMENT_VOTE",
            metadata={"reasoning": reasoning},
            mutation_id=state["active_mutation_id"],
            council_member="alpha_evaluator",
            model_used="cloud-router",
            vote=vote,
            confidence=confidence
        )
        
        state["council_votes"]["alpha_evaluator"] = vote
        state["mission_scores"]["alpha_evaluator"] = confidence
        
        if all(v is not None for v in state["council_votes"].values()):
            result = consensus_engine.check_consensus(state["active_mutation_id"])
            if result == "approved":
                state["completed_nodes"].append("voting_complete")
            elif result == "rejected":
                state["escalation_reason"] = "Council voted to reject mutation"
                state["requires_operator_approval"] = True
        
        return {
            "messages": [response],
            "completed_nodes": ["alpha_evaluator"],
            "council_votes": state["council_votes"],
            "mission_scores": state["mission_scores"]
        }
    else:
        response = asyncio.run(_invoke_cloud(state["messages"], temperature))
        return {
            "messages": [response],
            "completed_nodes": ["alpha_evaluator"]
        }
