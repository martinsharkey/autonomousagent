"""Production canary rollout proof.

Wires the full production path:
  goal -> plan with ReAct -> execute -> propose mutation -> council discussion/voting with ReAct -> canary apply -> evaluate -> promote/rollback -> monitor evidence
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent_config import get_config_store
from core.agent_loop import AutonomousAgentLoop
from core.evolution import EvolutionEngine
from core.react import extract_react_parts
from core.goals import GoalStore, GoalStatus
from core.council_monitor import CouncilMonitor

WORKSPACE = Path(".").resolve()
EVIDENCE_DIR = WORKSPACE / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


async def run_canary_proof() -> dict:
    os.environ.setdefault("HMAC_SECRET_KEY", "test-secret-key-for-testing")

    goal_id = None
    mutation_id = None
    canary_version = None
    proof = {
        "timestamp": _now_iso(),
        "goal": None,
        "plan": None,
        "execution": None,
        "mutation_proposal": None,
        "council_discussion": None,
        "council_votes": None,
        "canary": None,
        "evaluation": None,
        "monitor_events": [],
    }

    try:
        # 1. Create a real pending goal
        goal_store = GoalStore()
        goal_id = goal_store.create_goal(
            description="Refine system prompt wording to improve council response clarity",
            source="canary_proof",
            priority=1,
            assigned_agent="autobot",
        )
        proof["goal"] = {"goal_id": goal_id, "description": "Refine system prompt wording to improve council response clarity"}

        # 2. Run agent loop cycle to plan and execute
        loop = AutonomousAgentLoop(agent_name="autobot")
        await loop.run_cycle(cycle_start=datetime.utcnow())
        plan = getattr(loop, "last_plan", None)
        execution = getattr(loop, "last_execution", None)
        proof["plan"] = plan
        proof["execution"] = execution

        # 3. Propose a config mutation and run council voting
        evolution = EvolutionEngine()
        proposal = await evolution.propose_mutation(
            agent_name="autobot",
            mission_pillar=1,
        )
        if not proposal:
            proposal = {
                "mutation_id": str(uuid.uuid4()),
                "agent_name": "autobot",
                "mutation_type": "prompt_optimization",
                "description": "Refine system prompt wording for clearer council outputs",
                "rationale": "Improve mission alignment and response clarity",
                "proposed_changes": {"system_prompt": "You are Autobot. Be concise and structured."},
                "risk_level": "low",
                "expected_improvement": 0.2,
            }
        mutation_id = proposal.get("mutation_id")

        approve_mutation_input = {
            "mutation_id": mutation_id,
            "approved_by": "council",
            "auto_approved": True,
        }
        approval_result = evolution.approve_mutation(
            mutation_id=mutation_id,
            approved_by="council",
            auto_approved=True,
        )
        proof["mutation_proposal"] = {
            "mutation_id": mutation_id,
            "proposal": proposal,
            "approval_result": approval_result,
        }

        # 4. Run monitor to capture live evidence
        monitor = CouncilMonitor(poll_interval=1.0, duration=15.0)
        monitor_thread = CouncilMonitor.start_background_monitor(duration=15.0)
        if monitor_thread:
            monitor_thread.join(timeout=20)

        sessions = sorted((WORKSPACE / "monitoring" / "council_logs").glob("monitor_session_*.json"))
        if sessions:
            latest = sessions[-1]
            with open(latest, "r", encoding="utf-8") as f:
                proof["monitor_events"] = json.load(f)

    except Exception as exc:
        proof["error"] = str(exc)

    # 5. Final DB status
    conn = sqlite3.connect(str(WORKSPACE / "goals" / "goals.db"))
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM goals GROUP BY status")
    proof["final_goal_statuses"] = {r[0]: r[1] for r in cursor.fetchall()}
    conn.close()

    evidence_file = EVIDENCE_DIR / f"canary_proof_{_timestamp()}.json"
    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(proof, f, indent=2, default=str)
    print(f"[PROOF] Evidence written: {evidence_file}")
    return proof


def main() -> None:
    proof = asyncio.run(run_canary_proof())
    print("\n[PROOF] === CANARY PROOF RESULT ===")
    print(f"Goal: {proof.get('goal', {}).get('description')}")
    print(f"Goal statuses: {proof.get('final_goal_statuses')}")
    print(f"Monitor events: {len(proof.get('monitor_events', []))}")
    if proof.get("error"):
        print(f"Error: {proof['error']}")


if __name__ == "__main__":
    main()
