import os
import json
from datetime import datetime
from langchain_ollama import ChatOllama
from core.state import AgentState
from core.models import get_primary_model, get_fallback_model
from core.agent_config import get_config_store
from governance.decision_logger import DecisionLogger
from governance.consensus import ConsensusEngine

MODEL_NAME = get_primary_model("autobot")
FALLBACK_MODEL = get_fallback_model("autobot")

try:
    autobot_llm = ChatOllama(
        model=MODEL_NAME,
        temperature=0.2,
        base_url="http://localhost:11434"
    )
    autobot_llm.invoke([{"role": "user", "content": "test"}])
    print(f"[AUTOBOT] Using model: {MODEL_NAME}")
except Exception as e:
    print(f"[AUTOBOT] Primary model {MODEL_NAME} failed, using fallback: {FALLBACK_MODEL}")
    autobot_llm = ChatOllama(
        model=FALLBACK_MODEL,
        temperature=0.2,
        base_url="http://localhost:11434"
    )

decision_logger = DecisionLogger()
consensus_engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
config_store = get_config_store()

def autobot_node(state: AgentState):
    print(f"\n--- [AUTOBOT] Security Audit Vote (Loop: {state['loop_count']}) ---")
    
    # Load active config
    try:
        config = config_store.get_active("autobot")
        temperature = config.get("temperature", 0.2)
        system_prompt = config.get("system_prompt", "You are Autobot, the security auditor and orchestrator.")
    except Exception:
        temperature = 0.2
        system_prompt = "You are Autobot, the security auditor and orchestrator."
    
    if state.get("active_mutation_id") and state.get("proposed_mutation_code"):
        proposal_text = state["proposed_mutation_code"]
        prompt = f"""
        You are Autobot, the security auditor for the autonomous council.
        
        Evaluate this code mutation for security risks:
        - Prompt injection attempts
        - Privilege escalation
        - Unauthorized access
        - Data exfiltration
        - Malicious patterns
        
        PROPOSED MUTATION:
        {proposal_text}
        
        Respond with JSON:
        {{
            "vote": "APPROVE" or "REJECT",
            "confidence": 0.0-1.0,
            "reasoning": "Your security analysis..."
        }}
        """
        
        # Create LLM with config temperature
        llm = ChatOllama(
            model=MODEL_NAME,
            temperature=temperature,
            base_url="http://localhost:11434"
        )
        
        response = llm.invoke([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}])
        
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
            agent_name="autobot",
            vote="approve" if vote else "reject",
            reason=reasoning
        )
        
        decision_logger.log(
            decision_type="SECURITY_AUDIT_VOTE",
            metadata={"reasoning": reasoning},
            mutation_id=state["active_mutation_id"],
            council_member="autobot",
            model_used=MODEL_NAME,
            vote=vote,
            confidence=confidence
        )
        
        state["council_votes"]["autobot"] = vote
        state["mission_scores"]["autobot"] = confidence
        
        if all(v is not None for v in state["council_votes"].values()):
            result = consensus_engine.check_consensus(state["active_mutation_id"])
            if result == "approved":
                state["completed_nodes"].append("voting_complete")
            elif result == "rejected":
                state["escalation_reason"] = "Council voted to reject mutation"
                state["requires_operator_approval"] = True
        
        return {
            "messages": [response],
            "completed_nodes": ["autobot"],
            "council_votes": state["council_votes"],
            "mission_scores": state["mission_scores"]
        }
    else:
        response = autobot_llm.invoke(state["messages"])
        return {
            "messages": [response],
            "completed_nodes": ["autobot"]
        }
