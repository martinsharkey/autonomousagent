"""Integration tests for self-mutation Steps 2–5.

Covers:
- proposer fallback behavior
- council vote path
- canary/fleet rollout
- file allowlist rejections
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.timeout(30)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.evolution import (
    get_evolution_engine,
    MutationStatus,
    MutationType,
    propose_mutation,
    approve_mutation,
    implement_mutation,
)
from core.mutation_proposer import propose_mutation as propose_mutation_from_performance


@pytest.fixture(autouse=True)
def _clear_engine():
    engine = get_evolution_engine()
    engine.mutations.clear()
    try:
        from core.mutation_deduplicator import get_deduplicator
        get_deduplicator().clear()
    except Exception:
        pass
    yield
    engine.mutations.clear()
    try:
        from core.mutation_deduplicator import get_deduplicator
        get_deduplicator().clear()
    except Exception:
        pass


def test_proposer_fallback_returns_dict():
    import asyncio

    result = asyncio.run(
        propose_mutation_from_performance(
            agent_name="autobot",
            performance={"success_rate": 0.1},
        )
    )
    assert result is None or isinstance(result, dict)
    if isinstance(result, dict):
        assert "mutation_type" in result or "proposed_changes" in result


def test_council_vote_path_medium_risk():
    import asyncio

    engine = get_evolution_engine()
    mutation = propose_mutation(
        agent_name="autobot",
        mutation_type=MutationType.PARAMETER_ADJUSTMENT,
        description="Self-evolve, optimize, feedback, mutation, evolution: council vote proof",
        rationale="Medium-risk change requires real council votes",
        proposed_changes={"max_retries": 4},
        expected_improvement=0.1,
        risk_level="medium",
    )
    assert mutation.status == MutationStatus.PENDING_APPROVAL

    result = asyncio.run(engine.collect_council_votes(mutation.mutation_id))
    assert "votes" in result
    votes = result.get("votes", {})
    assert len(votes) >= 2
    reasons = [v.get("reason", "") for v in votes.values() if v.get("reason")]
    assert len(set(reasons)) >= 1


def test_allowlist_rejects_denied_paths():
    engine = get_evolution_engine()
    with pytest.raises(ValueError, match="denied by policy"):
        propose_mutation(
            agent_name="autobot",
            mutation_type=MutationType.BEHAVIOR_CHANGE,
            description="bad path",
            rationale="should fail",
            proposed_changes={
                "file_changes": [{"path": ".env", "kind": "edit", "content": "BAD"}]
            },
            expected_improvement=0.01,
            risk_level="high",
        )


def test_allowlist_rejects_non_allowlisted_paths():
    engine = get_evolution_engine()
    with pytest.raises(ValueError, match="denied by policy"):
        propose_mutation(
            agent_name="autobot",
            mutation_type=MutationType.BEHAVIOR_CHANGE,
            description="bad path",
            rationale="should fail",
            proposed_changes={
                "file_changes": [{"path": "random/secret.py", "kind": "edit", "content": "BAD"}]
            },
            expected_improvement=0.01,
            risk_level="high",
        )


def test_canary_fleet_rollout():
    engine = get_evolution_engine()

    mutation = propose_mutation(
        agent_name="autobot",
        mutation_type=MutationType.PARAMETER_ADJUSTMENT,
        description="Self-evolve, optimize, feedback: canary then fleet rollout",
        rationale="Prove config rollout path",
        proposed_changes={"max_retries": 4},
        expected_improvement=0.1,
        risk_level="low",
    )
    assert mutation.status == MutationStatus.PENDING_APPROVAL

    approve_mutation(mutation.mutation_id, approved_by="integration_test")
    mutation = engine.get_mutation(mutation.mutation_id)
    assert mutation.status in (MutationStatus.APPROVED, MutationStatus.IMPLEMENTED)

    if mutation.status == MutationStatus.APPROVED:
        result = implement_mutation(mutation.mutation_id)
        assert result.get("success") is True
        mutation = engine.get_mutation(mutation.mutation_id)
        assert mutation.status == MutationStatus.IMPLEMENTED

    from core.rollout import start_canary, advance_rollout, rollout_status

    canary = start_canary(mutation.mutation_id)
    assert canary["success"] is True
    assert canary["state"] == "canary"
    assert canary["canary_agent"] == "autobot"

    fleet = advance_rollout(mutation.mutation_id)
    if fleet.get("success"):
        assert fleet["agent"] == "alpha_evaluator"
        assert fleet["state"] in ("rolling_out", "complete")
    else:
        assert fleet.get("error") == "eval regression"
        assert fleet.get("rolled_back") is True

    status = rollout_status(mutation.mutation_id)
    assert status["canary"] == "autobot"
    assert status["state"] in ("canary", "rolling_out", "failed", "complete")
