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
        config = config_store.get_active_with_defaults(agent_name)
        return config
    except Exception:
        return DEFAULT_CONFIGS.get(agent_name, {})


def _safe_run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result(timeout=120)


async def _invoke_cloud(messages, context: str = "default"):
    """Invoke LLM through cloud router."""
    try:
        temperature = get_dynamic_temperature("alpha_evaluator", context)
        response = await llm_router.route_request(
            messages=messages,
            temperature=temperature
        )
        # Extract content from response
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        return AIMessage(content=content)
    except Exception as e:
        print(f"[ALPHA] Cloud router failed: {e}")
        raise

def alpha_node(state: AgentState):
    print(f"\n--- [ALPHA] Mission Alignment & Test Readiness Vote (Loop: {state['loop_count']}) ---")
    
    config = _load_active_config("alpha_evaluator")
    base_system_prompt = config.get("system_prompt", "You are Alpha, the mission alignment evaluator.")
    system_prompt = build_react_system_prompt(inject_full_context(base_system_prompt, "alpha_evaluator"), "Alpha Evaluator")
    
    error_feedback = state.get("error_feedback") or []
    last_error_trace = state.get("last_error_trace")
    
    if error_feedback and not state.get("active_mutation_id"):
        last_error = error_feedback[-1]
        print(f"[ALPHA] Self-correcting from error: {last_error.get('error_type')} - {last_error.get('error_message')}")
        user_prompt = build_self_correction_prompt("Alpha Evaluator", last_error, state.get("reasoning_traces", []))
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        try:
            response = _safe_run(_invoke_cloud(messages, "self_correction"))
            content = response.content
            reasoning, action_text = extract_react_parts(content)
            trace = f"[alpha] SELF-CORRECTION: {reasoning}" if reasoning else f"[alpha] SELF-CORRECTION: {content[:200]}"
            state["reasoning_traces"].append(trace)
            revised_code = None
            try:
                decision = json.loads(action_text)
                revised_code = decision.get("revised_code")
            except (json.JSONDecodeError, ValueError):
                pass
            return {
                "messages": [response],
                "completed_nodes": ["alpha_evaluator"],
                "reasoning_traces": state.get("reasoning_traces", []),
                "error_feedback": state.get("error_feedback", []),
                "last_error_trace": reasoning,
                "proposed_mutation_code": revised_code,
            }
        except Exception as e:
            print(f"[ALPHA] Self-correction failed: {e}")
            return {
                "messages": [AIMessage(content=f"Alpha self-correction failed: {e}")],
                "completed_nodes": ["alpha_evaluator"],
                "reasoning_traces": state.get("reasoning_traces", []),
                "error_feedback": state.get("error_feedback", []),
            }
    
    if state.get("active_mutation_id") and state.get("proposed_mutation_code"):
        proposal_text = state["proposed_mutation_code"]
        mission_rationale = state.get("mission_rationale", "No mission rationale provided")
        user_prompt = build_react_voter_prompt("Alpha Evaluator", proposal_text, mission_rationale)
        
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        
        try:
            response = _safe_run(_invoke_cloud(messages, "mutation_evaluation"))
            content = response.content
            reasoning, action_text = extract_react_parts(content)
            
            trace = f"[alpha] {reasoning}" if reasoning else f"[alpha] {content[:200]}"
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
            error_feedback = build_error_feedback("alpha_evaluator", e, {"mutation_id": state.get("active_mutation_id")})
            state["error_feedback"].append(error_feedback)
            print(f"[ALPHA] Vote failed: {e}")
            return {
                "messages": [AIMessage(content=f"Alpha evaluation failed: {e}")],
                "completed_nodes": ["alpha_evaluator"],
                "council_votes": state.get("council_votes", {}),
                "mission_scores": state.get("mission_scores", {}),
                "reasoning_traces": state.get("reasoning_traces", []),
                "error_feedback": state.get("error_feedback", []),
            }
        
        consensus_engine.cast_vote(
            proposal_id=state["active_mutation_id"],
            agent_name="alpha_evaluator",
            vote="approve" if vote else "reject",
            reason=reasoning_text
        )
        
        decision_logger.log(
            decision_type="MISSION_ALIGNMENT_VOTE",
            metadata={"reasoning": reasoning_text},
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
            "mission_scores": state["mission_scores"],
            "reasoning_traces": state.get("reasoning_traces", []),
            "error_feedback": state.get("error_feedback", []),
        }
    else:
        try:
            response = _safe_run(_invoke_cloud([{"role": "system", "content": system_prompt}, *state["messages"]], "default"))
            content = response.content
            reasoning, _ = extract_react_parts(content)
            if reasoning:
                state["reasoning_traces"].append(f"[alpha] {reasoning}")
            return {
                "messages": [response],
                "completed_nodes": ["alpha_evaluator"],
                "reasoning_traces": state.get("reasoning_traces", []),
            }
        except Exception as e:
            error_feedback = build_error_feedback("alpha_evaluator", e)
            state["error_feedback"].append(error_feedback)
            print(f"[ALPHA] General response failed: {e}")
            return {
                "messages": [AIMessage(content=f"Alpha error: {e}")],
                "completed_nodes": ["alpha_evaluator"],
                "reasoning_traces": state.get("reasoning_traces", []),
                "error_feedback": state.get("error_feedback", []),
            }
