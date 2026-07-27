import os
import json
import asyncio
from datetime import datetime
from langchain_core.messages import AIMessage
from core.api_router import get_llm_router
from core.state import AgentState
from core.models import get_primary_model, get_fallback_model
from core.agent_config import get_config_store
from governance.decision_logger import DecisionLogger
from governance.consensus import ConsensusEngine
from core.agent_context import inject_mission_context

MODEL_NAME = get_primary_model("beta_worker")
FALLBACK_MODEL = get_fallback_model("beta_worker")

# Initialize cloud router
llm_router = get_llm_router()
print(f"[BETA] Cloud-first LLM router initialized")

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


async def _invoke_cloud(messages, temperature=0.3):
    """Invoke LLM through cloud router."""
    try:
        response = await llm_router.route_request(
            messages=messages,
            temperature=temperature
        )
        # Extract content from response
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        return AIMessage(content=content)
    except Exception as e:
        print(f"[BETA] Cloud router failed: {e}")
        raise

def beta_node(state: AgentState):
    print(f"\n--- [BETA] Feasibility Vote (Loop: {state['loop_count']}) ---")
    
    # Load active config (mid-session reload)
    config = _load_active_config("beta_worker")
    temperature = config.get("temperature", 0.3)
    system_prompt = config.get("system_prompt", "You are Beta, the feasibility evaluator and worker.")
    
    if state.get("active_mutation_id") and state.get("proposed_mutation_code"):
        proposal_text = state["proposed_mutation_code"]
        
        prompt = f"""
        You are Beta, the feasibility evaluator for the autonomous council.
        
        Evaluate this code mutation for:
        - Syntax correctness
        - Compatibility with existing codebase
        - Implementation feasibility
        - Test coverage adequacy
        
        PROPOSED MUTATION:
        {proposal_text}
        
        Respond with JSON:
        {{
            "vote": "APPROVE" or "REJECT",
            "confidence": 0.0-1.0,
            "syntax_valid": true/false,
            "compatible": true/false,
            "feasible": true/false,
            "reasoning": "Your feasibility analysis..."
        }}
        """
        
        messages = [{"role": "system", "content": inject_mission_context(system_prompt)}, {"role": "user", "content": prompt}]
        
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
            agent_name="beta_worker",
            vote="approve" if vote else "reject",
            reason=reasoning
        )
        
        decision_logger.log(
            decision_type="FEASIBILITY_VOTE",
            metadata={"reasoning": reasoning},
            mutation_id=state["active_mutation_id"],
            council_member="beta_worker",
            model_used="cloud-router",
            vote=vote,
            confidence=confidence
        )
        
        state["council_votes"]["beta_worker"] = vote
        state["mission_scores"]["beta_worker"] = confidence
        
        if all(v is not None for v in state["council_votes"].values()):
            result = consensus_engine.check_consensus(state["active_mutation_id"])
            if result == "approved":
                state["completed_nodes"].append("voting_complete")
            elif result == "rejected":
                state["escalation_reason"] = "Council voted to reject mutation"
                state["requires_operator_approval"] = True
        
        return {
            "messages": [response],
            "completed_nodes": ["beta_worker"],
            "council_votes": state["council_votes"],
            "mission_scores": state["mission_scores"]
        }
    else:
        response = asyncio.run(_invoke_cloud(state["messages"], temperature))
        return {
            "messages": [response],
            "completed_nodes": ["beta_worker"]
        }
