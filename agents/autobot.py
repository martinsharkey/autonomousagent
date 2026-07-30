import os
import json
import asyncio
from datetime import datetime
from langchain_core.messages import AIMessage
from core.api_router import get_llm_router
from core.state import AgentState
from core.models import get_primary_model, get_fallback_model
from core.agent_config import get_config_store, DEFAULT_CONFIGS
from governance.decision_logger import DecisionLogger
from governance.consensus import ConsensusEngine
from core.agent_context import inject_full_context
from core.temperature_selector import get_dynamic_temperature
from core.react import extract_react_parts, build_react_system_prompt, build_react_voter_prompt, build_error_feedback

MODEL_NAME = get_primary_model("autobot")
FALLBACK_MODEL = get_fallback_model("autobot")

# Initialize cloud router
llm_router = get_llm_router()
print(f"[AUTOBOT] Cloud-first LLM router initialized")

decision_logger = DecisionLogger()
consensus_engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
config_store = get_config_store()


def _load_active_config(agent_name: str):
    """Load current active config for mid-session config reloading."""
    try:
        config = config_store.get_active_with_defaults(agent_name)
        return config
    except Exception:
        return DEFAULT_CONFIGS.get(agent_name, {})


def _safe_run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=120)


async def _invoke_cloud(messages, context: str = "default"):
    """Invoke LLM through cloud router."""
    try:
        temperature = get_dynamic_temperature("autobot", context)
        response = await llm_router.route_request(
            messages=messages,
            temperature=temperature
        )
        # Extract content from response
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        return AIMessage(content=content)
    except Exception as e:
        print(f"[AUTOBOT] Cloud router failed: {e}")
        raise

def autobot_node(state: AgentState):
    print(f"\n--- [AUTOBOT] Security Audit Vote (Loop: {state['loop_count']}) ---")
    
    # Load active config (mid-session reload)
    config = _load_active_config("autobot")
    base_system_prompt = config.get("system_prompt", "You are Autobot, the security auditor and orchestrator.")
    system_prompt = build_react_system_prompt(inject_full_context(base_system_prompt, "autobot"), "Autobot")
    
    if state.get("active_mutation_id") and state.get("proposed_mutation_code"):
        proposal_text = state["proposed_mutation_code"]
        mission_rationale = state.get("mission_rationale", "No mission rationale provided")
        user_prompt = build_react_voter_prompt("Autobot", proposal_text, mission_rationale)
        
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        
        try:
            response = _safe_run(_invoke_cloud(messages, "security_audit"))
            content = response.content
            reasoning, action_text = extract_react_parts(content)
            
            trace = f"[autobot] {reasoning}" if reasoning else f"[autobot] {content[:200]}"
            state["reasoning_traces"].append(trace)
            
            try:
                decision = json.loads(action_text)
                vote = decision.get("vote", "REJECT").upper() == "APPROVE"
                confidence = float(decision.get("confidence", 0.5))
                reasoning_text = decision.get("reasoning", "No reasoning provided")
            except (json.JSONDecodeError, ValueError):
                vote = False
                confidence = 0.0
                reasoning_text = f"Failed to parse action: {action_text}"
            
        except Exception as e:
            error_feedback = build_error_feedback("autobot", e, {"mutation_id": state.get("active_mutation_id")})
            state["error_feedback"].append(error_feedback)
            print(f"[AUTOBOT] Vote failed: {e}")
            return {
                "messages": [AIMessage(content=f"Autobot voting failed: {e}")],
                "completed_nodes": ["autobot"],
                "council_votes": state.get("council_votes", {}),
                "mission_scores": state.get("mission_scores", {}),
                "reasoning_traces": state.get("reasoning_traces", []),
                "error_feedback": state.get("error_feedback", []),
            }
        
        consensus_engine.cast_vote(
            proposal_id=state["active_mutation_id"],
            agent_name="autobot",
            vote="approve" if vote else "reject",
            reason=reasoning_text
        )
        
        decision_logger.log(
            decision_type="SECURITY_AUDIT_VOTE",
            metadata={"reasoning": reasoning_text},
            mutation_id=state["active_mutation_id"],
            council_member="autobot",
            model_used="cloud-router",
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
            "mission_scores": state["mission_scores"],
            "reasoning_traces": state.get("reasoning_traces", []),
            "error_feedback": state.get("error_feedback", []),
        }
    else:
        # Use cloud router for general messages
        try:
            response = _safe_run(_invoke_cloud([{"role": "system", "content": system_prompt}, *state["messages"]], "default"))
            content = response.content
            reasoning, _ = extract_react_parts(content)
            if reasoning:
                state["reasoning_traces"].append(f"[autobot] {reasoning}")
            return {
                "messages": [response],
                "completed_nodes": ["autobot"],
                "reasoning_traces": state.get("reasoning_traces", []),
            }
        except Exception as e:
            error_feedback = build_error_feedback("autobot", e)
            state["error_feedback"].append(error_feedback)
            print(f"[AUTOBOT] General response failed: {e}")
            return {
                "messages": [AIMessage(content=f"Autobot error: {e}")],
                "completed_nodes": ["autobot"],
                "reasoning_traces": state.get("reasoning_traces", []),
                "error_feedback": state.get("error_feedback", []),
            }
