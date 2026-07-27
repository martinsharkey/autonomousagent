"""Config rollout: canary -> fleet with eval gate."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.agent_config import get_config_store
from core.evolution import get_evolution_engine
from core.evaluation import run_evaluation_suite


def start_canary(mutation_id: str) -> Dict[str, Any]:
    engine = get_evolution_engine()
    engine._load_existing_mutations()
    mutation = engine.get_mutation(mutation_id)
    if not mutation:
        return {"success": False, "error": "Mutation not found"}
    if mutation.status.value not in ("approved", "implemented"):
        return {"success": False, "error": "Mutation not approved"}

    targets = _fleet_targets(mutation.agent_name)
    mutation.rollout_state = "canary"
    mutation.rollout_targets = targets
    mutation.rollout_current_index = 0
    mutation.rollout_started_at = _utc_now()
    engine._save_mutation(mutation)

    return {
        "success": True,
        "mutation_id": mutation.mutation_id,
        "state": "canary",
        "canary_agent": mutation.agent_name,
        "targets": targets,
        "soak_cycles": mutation.rollout_soak_cycles,
    }


def advance_rollout(mutation_id: str) -> Dict[str, Any]:
    engine = get_evolution_engine()
    engine._load_existing_mutations()
    mutation = engine.get_mutation(mutation_id)
    if not mutation:
        return {"success": False, "error": "Mutation not found"}

    if mutation.rollout_state == "complete":
        return {"success": False, "error": "Rollout already complete"}
    if mutation.rollout_state == "failed":
        return {"success": False, "error": "Rollout already failed"}

    if mutation.rollout_state is None:
        canary = start_canary(mutation_id)
        if not canary.get("success"):
            return canary
        mutation = engine.get_mutation(mutation_id)

    config_store = get_config_store()
    targets = mutation.rollout_targets
    idx = mutation.rollout_current_index

    if idx >= len(targets):
        mutation.rollout_state = "complete"
        mutation.rollout_completed_at = _utc_now()
        engine._save_mutation(mutation)
        return {"success": True, "state": "complete", "mutation_id": mutation.mutation_id}

    next_agent = targets[idx]
    parent_version = config_store.get_active(next_agent).get("version", "v1.0.0")

    try:
        new_version = config_store.create_version(
            agent_name=next_agent,
            changes=mutation.proposed_changes,
            parent_version=parent_version,
            mutation_id=mutation.mutation_id,
        )
    except Exception as exc:
        return {"success": False, "error": f"create_version failed: {exc}"}

    try:
        eval_results = run_evaluation_suite(next_agent, new_version)
    except Exception as exc:
        config_store.rollback(next_agent, parent_version)
        _maybe_rollback_canary(mutation, config_store)
        mutation.rollout_state = "failed"
        engine._save_mutation(mutation)
        return {"success": False, "error": f"eval failed: {exc}", "rolled_back": True}

    previous_score = config_store.get_active(next_agent).get("last_eval_score", 0.5)
    new_score = eval_results.get("score", 0.0)
    tolerance = 0.05

    if new_score >= previous_score - tolerance:
        config_store.promote(next_agent, new_version)
        mutation.rollout_current_index = idx + 1
        if mutation.rollout_current_index >= len(targets):
            mutation.rollout_state = "complete"
            mutation.rollout_completed_at = _utc_now()
        else:
            mutation.rollout_state = "rolling_out"
        engine._save_mutation(mutation)
        return {
            "success": True,
            "state": mutation.rollout_state,
            "agent": next_agent,
            "version": new_version,
            "score": new_score,
            "mutation_id": mutation.mutation_id,
        }

    config_store.rollback(next_agent, parent_version)
    _maybe_rollback_canary(mutation, config_store)
    mutation.rollout_state = "failed"
    engine._save_mutation(mutation)
    return {
        "success": False,
        "error": "eval regression",
        "agent": next_agent,
        "rolled_back": True,
        "mutation_id": mutation.mutation_id,
        "score_regression": new_score - previous_score,
    }


def rollout_status(mutation_id: str) -> Dict[str, Any]:
    engine = get_evolution_engine()
    engine._load_existing_mutations()
    mutation = engine.get_mutation(mutation_id)
    if not mutation:
        return {"success": False, "error": "Mutation not found"}

    targets = mutation.rollout_targets or _fleet_targets(mutation.agent_name)
    current_idx = mutation.rollout_current_index or 0
    completed = targets[:current_idx]
    current = targets[current_idx] if current_idx < len(targets) else None
    pending = targets[current_idx + 1:]

    config_store = get_config_store()
    versions = {}
    for agent in targets:
        try:
            versions[agent] = config_store.get_active(agent).get("version")
        except Exception:
            versions[agent] = None

    return {
        "mutation_id": mutation.mutation_id,
        "state": mutation.rollout_state,
        "canary": mutation.agent_name,
        "completed": completed,
        "current": current,
        "pending": pending,
        "versions": versions,
        "started_at": mutation.rollout_started_at,
        "completed_at": mutation.rollout_completed_at,
    }


def _fleet_targets(canary_agent: str) -> List[str]:
    fleet = ["autobot", "alpha_evaluator", "beta_worker"]
    return [a for a in fleet if a != canary_agent]


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _maybe_rollback_canary(mutation, config_store) -> None:
    if mutation.rollout_state != "canary":
        return
    try:
        canary_version = config_store.get_active(mutation.agent_name).get("parent_version")
        if canary_version:
            config_store.rollback(mutation.agent_name, canary_version)
    except Exception as exc:
        print(f"[ROLLOUT] Optional canary rollback failed: {exc}")
