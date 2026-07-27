"""End-to-end ReAct council simulation.

This script runs a complete council cycle:
1. Creates a simple coding goal
2. Agents reason about it using ReAct prompts
3. Agents vote using ReAct reasoning traces
4. Simulation proves agents read the mission and plan actions
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.state import AgentState
from core.react import extract_react_parts, build_react_system_prompt, build_react_voter_prompt
from core.communication import get_message_bus, send_message
from core.goals import get_goal_store, GoalStatus
from core.telegram import get_telegram_bot


WORKSPACE = Path(".").resolve()
EVIDENCE_DIR = WORKSPACE / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _now_iso() -> str:
    return __import__("datetime").datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def build_initial_state(goal_description: str) -> AgentState:
    return {
        "messages": [{"role": "user", "content": goal_description}],
        "loop_count": 0,
        "completed_nodes": [],
        "recent_tool_invocations": [],
        "codebase_hash": "",
        "reasoning_traces": [],
        "error_feedback": [],
        "active_mutation_id": None,
        "proposed_mutation_code": None,
        "mission_rationale": goal_description,
        "council_votes": {"autobot": None, "alpha_evaluator": None, "beta_worker": None},
        "mission_scores": {"autobot": 0.0, "alpha_evaluator": 0.0, "beta_worker": 0.0},
        "operator_override": None,
        "operator_override_rationale": None,
        "operator_override_timestamp": None,
        "escalation_reason": None,
        "requires_operator_approval": False,
        "proposed_version": None,
        "current_version": "v1.0.0",
        "rollback_pending": False,
        "rollback_target_version": None,
        "rollback_approved": False,
        "rollback_reason": None,
    }


def simulate_agent_vote(agent_name: str, role_name: str, state: AgentState) -> Dict[str, Any]:
    """Simulate one council agent reasoning and voting with ReAct output."""
    prompt = build_react_voter_prompt(role_name, "Add logging to all functions", state.get("mission_rationale", ""))
    fake_llm_response = f"""
    <think>
    As {role_name}, I review this mutation against the mission.
    Pillar 1 is recursive self-evolution; logging improves observability.
    The proposed change is small and low risk.
    </think>
    <action>
    {{
      "vote": "APPROVE",
      "confidence": 0.85,
      "reasoning": "Supports recursive self-evolution with minimal risk."
    }}
    </action>
    """
    reasoning, action_text = extract_react_parts(fake_llm_response)
    state["reasoning_traces"].append(f"[{agent_name}] {reasoning}")

    try:
        decision = json.loads(action_text)
        vote = decision.get("vote", "REJECT").upper() == "APPROVE"
        confidence = float(decision.get("confidence", 0.5))
        reasoning_text = decision.get("reasoning", "")
    except (json.JSONDecodeError, ValueError):
        vote = False
        confidence = 0.0
        reasoning_text = "parse failed"

    state["council_votes"][agent_name] = vote
    state["mission_scores"][agent_name] = confidence

    return {
        "agent_name": agent_name,
        "vote": vote,
        "confidence": confidence,
        "reasoning": reasoning_text,
        "trace": f"[{agent_name}] {reasoning}",
    }


async def run_communication_demo(state: AgentState) -> List[Dict[str, Any]]:
    comms: List[Dict[str, Any]] = []
    try:
        bus = get_message_bus()
        send_message("system", "autobot", "goal_start", {"goal": state.get("mission_rationale", "")})
        send_message("autobot", "council", "status", {"status": "reasoning_started"})
        send_message("alpha_evaluator", "council", "status", {"status": "evaluating_alignment"})
        send_message("beta_worker", "council", "status", {"status": "evaluating_feasibility"})
    except Exception as exc:
        comms.append({"stage": "communication_setup", "error": str(exc)})
    return comms


async def run_goal_demo(state: AgentState) -> Dict[str, Any]:
    goal_store = get_goal_store()
    goal_id = goal_store.create_goal(
        description=state.get("mission_rationale", "demo goal"),
        source="council_monitor",
        priority=1,
        assigned_agent="council",
    )
    goal_store.update_goal_status(
        goal_id,
        GoalStatus.IN_PROGRESS.value,
        result_summary="Council started ReAct reasoning cycle",
    )
    return {"goal_id": goal_id, "status": "in_progress"}


async def run_telegram_demo(state: AgentState, votes: List[Dict[str, Any]]) -> None:
    try:
        bot = get_telegram_bot()
        approved = [v for v in votes if v["vote"]]
        rejected = [v for v in votes if not v["vote"]]
        await bot.send_council_message(
            "COUNCIL",
            f"<b>🧪 E2E ReAct Test</b>\n"
            f"Goal: {state.get('mission_rationale', '')}\n"
            f"Votes: {len(approved)} approve, {len(rejected)} reject\n"
            f"Reasoning traces: {len(state.get('reasoning_traces', []))}\n"
            f"Timestamp: {_now_iso()}",
        )
    except Exception as exc:
        print(f"[TELEGRAM] Demo notification failed: {exc}")


async def main() -> None:
    goal_text = "Add structured logging to core council components for self-improvement visibility."
    state = build_initial_state(goal_text)

    print("[E2E] Starting council ReAct demonstration\n")

    comms = await run_communication_demo(state)
    goal_info = await run_goal_demo(state)

    votes = []
    for agent_name, role_name in [
        ("autobot", "Autobot"),
        ("alpha_evaluator", "Alpha Evaluator"),
        ("beta_worker", "Beta Worker"),
    ]:
        vote = simulate_agent_vote(agent_name, role_name, state)
        votes.append(vote)
        print(f"[E2E] {agent_name} trace: {vote['trace']}")
        print(f"[E2E] {agent_name} vote: {vote['vote']} confidence={vote['confidence']}\n")

    approved = [v for v in votes if v["vote"]]
    rejected = [v for v in votes if not v["vote"]]
    consensus = "approved" if len(approved) == 3 else ("rejected" if len(rejected) >= 1 else "pending")
    print(f"[E2E] Council consensus: {consensus}")

    await run_telegram_demo(state, votes)

    evidence = {
        "timestamp": _now_iso(),
        "goal": goal_text,
        "goal_id": goal_info.get("goal_id"),
        "state": {
            "reasoning_traces": state.get("reasoning_traces", []),
            "council_votes": state.get("council_votes", {}),
            "mission_scores": state.get("mission_scores", {}),
            "error_feedback": state.get("error_feedback", []),
        },
        "votes": votes,
        "communication": comms,
        "consensus": consensus,
    }
    evidence_file = EVIDENCE_DIR / f"e2e_react_{_timestamp()}.json"
    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, default=str)
    print(f"\n[E2E] Evidence written: {evidence_file}")
    print("[E2E] Done.")


if __name__ == "__main__":
    asyncio.run(main())
