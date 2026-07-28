"""Prove the goal execution pipeline works end-to-end."""
from __future__ import annotations

import asyncio
import sqlite3
import uuid
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent_config import get_config_store
from core.planning import AgentPlanner
from core.sandbox import execute_in_sandbox
from core.goals import GoalStore, GoalStatus


WORKSPACE = Path(".").resolve()


def create_pending_goal(description: str, agent: str = "autobot") -> str:
    goal_store = GoalStore()
    goal_id = goal_store.create_goal(
        description=description,
        source="e2e_proof",
        priority=1,
        assigned_agent=agent,
    )
    print(f"[PROOF] Created pending goal {goal_id[:12]}...: {description}")
    return goal_id


def run_planner_cycle(agent_name: str, goal_description: str) -> dict:
    print(f"\n[PROOF] === {agent_name} planner cycle ===")
    
    # Step 1: Verify config loads
    config_store = get_config_store()
    config = config_store.get_active_with_defaults(agent_name)
    print(f"[PROOF] Config loaded: version={config.get('version')}, temp={config.get('temperature')}")
    
    # Step 2: Create plan
    planner = AgentPlanner(agent_name)
    plan_result = planner.create_plan(goal_description)
    print(f"[PROOF] Plan status: {plan_result.get('status')}")
    if plan_result.get("status") != "created":
        print(f"[PROOF] Plan error: {plan_result.get('error')}")
        return {"status": "failed", "error": plan_result.get("error")}
    
    steps = plan_result.get("plan", {}).get("steps", [])
    print(f"[PROOF] Plan steps: {len(steps)}")
    for step in steps:
        print(f"  Step {step.get('step')}: {step.get('action')[:80]}...")
    
    # Step 3: Execute plan
    execution_result = planner.execute_plan(plan_result)
    print(f"[PROOF] Execution status: {execution_result.get('status')}")
    
    if execution_result.get("status") == "completed":
        results = execution_result.get("results", [])
        for r in results:
            print(f"  Step {r.get('step')} result: {str(r.get('output', r.get('error', '')))[:100]}")
    
    return execution_result


def mark_goal_complete(goal_id: str, result: dict) -> None:
    goal_store = GoalStore()
    status = GoalStatus.COMPLETED.value if result.get("status") == "completed" else GoalStatus.FAILED.value
    summary = f"Executed by planner, Status: {result.get('status')}"
    if result.get("failed_at_step"):
        summary += f", failed at step {result.get('failed_at_step')}"
    goal_store.update_goal_status(goal_id, status, result_summary=summary)
    print(f"\n[PROOF] Goal {goal_id[:12]}... marked as {status}")


def main() -> None:
    goal_text = "Create a simple Python hello world script and verify it runs"
    goal_id = create_pending_goal(goal_text)
    
    result = run_planner_cycle("autobot", goal_text)
    mark_goal_complete(goal_id, result)
    
    print("\n[PROOF] === SUMMARY ===")
    print(f"Goal: {goal_text}")
    print(f"Result: {result.get('status')}")
    
    # Check DB
    conn = sqlite3.connect(str(WORKSPACE / "goals" / "goals.db"))
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM goals GROUP BY status")
    rows = cursor.fetchall()
    print("Goal statuses:")
    for r in rows:
        print(f"  {r[0]}: {r[1]}")
    conn.close()


if __name__ == "__main__":
    main()
