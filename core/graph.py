from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy
from core.checkpointer import JSONCheckpointer
from core.state import AgentState
from agents.autobot import autobot_node
from agents.alpha_evaluator import alpha_node
from agents.beta_worker import beta_node
from core.semantic_cache import check_duplicate_invocation
from core.snapshots import capture_snapshot
from core.rollback import error_handler_node

local_retry = RetryPolicy(
    initial_interval=0.5,
    backoff_factor=2.0,
    max_attempts=3,
    jitter=True
)

def deterministic_router(state: AgentState) -> str:
    if state["loop_count"] >= 5:
        print(f"[SYSTEM OVERRIDE] TTL limit {state['loop_count']} breached. Terminating.")
        return "terminal_fallback"

    last_message = state["messages"][-1].content

    if "EXECUTE_CODE" in last_message:
        return "beta_worker"

    if "REVIEW_REQUIRED" in last_message:
        return "alpha_evaluator"

    if "CONSENSUS_REACHED" in last_message:
        return END

    return "autobot"

def autobot_with_cache(state: AgentState):
    duplicate = check_duplicate_invocation(state)
    if duplicate:
        return {
            "messages": [{"role": "system", "content": "SYSTEM OVERRIDE: YOU HAVE ALREADY TRIED THIS ACTION AND IT FAILED."}],
            "loop_count": state["loop_count"] + 1
        }
    result = autobot_node(state)
    capture_snapshot(state, "autobot")
    result["loop_count"] = state["loop_count"] + 1
    return result

def alpha_with_cache(state: AgentState):
    duplicate = check_duplicate_invocation(state)
    if duplicate:
        return {
            "messages": [{"role": "system", "content": "SYSTEM OVERRIDE: YOU HAVE ALREADY TRIED THIS ACTION AND IT FAILED."}],
            "loop_count": state["loop_count"] + 1
        }
    result = alpha_node(state)
    capture_snapshot(state, "alpha_evaluator")
    result["loop_count"] = state["loop_count"] + 1
    return result

def beta_with_cache(state: AgentState):
    duplicate = check_duplicate_invocation(state)
    if duplicate:
        return {
            "messages": [{"role": "system", "content": "SYSTEM OVERRIDE: YOU HAVE ALREADY TRIED THIS ACTION AND IT FAILED."}],
            "loop_count": state["loop_count"] + 1
        }
    result = beta_node(state)
    capture_snapshot(state, "beta_worker")
    result["loop_count"] = state["loop_count"] + 1
    return result

workflow = StateGraph(AgentState)

workflow.add_node("autobot", autobot_with_cache, retry=local_retry)
workflow.add_node("alpha_evaluator", alpha_with_cache, retry=local_retry)
workflow.add_node("beta_worker", beta_with_cache, retry=local_retry)
workflow.add_node("terminal_fallback", lambda state: {"messages": [{"role": "system", "content": "Task terminated due to loop limit."}]})
workflow.add_node("error_handler", error_handler_node)

workflow.add_edge(START, "autobot")

workflow.add_conditional_edges(
    "autobot",
    deterministic_router,
    {
        "beta_worker": "beta_worker",
        "alpha_evaluator": "alpha_evaluator",
        "terminal_fallback": "terminal_fallback",
        END: END
    }
)

workflow.add_edge("beta_worker", "autobot")
workflow.add_edge("alpha_evaluator", "autobot")

checkpointer = JSONCheckpointer(filepath="./checkpoints.json")
app = workflow.compile(checkpointer=checkpointer)
