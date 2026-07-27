#!/usr/bin/env python3
"""
Controlled autonomous mutation cycle test.

Demonstrates the full council-driven lifecycle without human intervention:
  1. Council member proposes a real code mutation with file_changes
  2. Council consensus votes across autobot / alpha_evaluator / beta_worker
  3. Mutation is approved and implemented
  4. Evidence artifacts are written to evidence/ for inspection

Run: pytest tests/test_autonomous_mutation_cycle.py -v --tb=short
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from core.evolution import (
    Mutation,
    MutationStatus,
    MutationType,
    get_evolution_engine,
    approve_mutation,
    implement_mutation,
    propose_mutation,
)
from governance.audit_log import read_audit_log
from governance.consensus import ConsensusEngine

REPO_ROOT = Path(".").resolve()
EVIDENCE_DIR = REPO_ROOT / "evidence" / "autonomous_mutation_cycle"
COUNCIL = ["autobot", "alpha_evaluator", "beta_worker"]


def _clean_evidence() -> None:
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR, ignore_errors=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def _clean_git_branches() -> None:
    output = subprocess.run(
        ["git", "branch", "--format=%(refname:short)"],
        capture_output=True,
        text=True,
        check=True,
    )
    for branch in [b.strip() for b in output.stdout.splitlines() if b.strip()]:
        if branch.startswith("test/mutation/"):
            subprocess.run(["git", "branch", "-D", branch], check=True, capture_output=True)


def _write_json(name: str, payload: dict) -> Path:
    path = EVIDENCE_DIR / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _append_report(title: str, body: str) -> None:
    path = EVIDENCE_DIR / "evidence_report.md"
    if not path.exists():
        path.write_text("# Autonomous Mutation Evidence Report\n\n", encoding="utf-8")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"## {title}\n\n{body}\n\n")


def test_autonomous_mutation_cycle_proposes_visible_content() -> None:
    """Council member proposes a mutation that carries real description and changes."""
    _clean_evidence()
    _clean_git_branches()

    engine = get_evolution_engine()
    engine.mutations.clear()

    description = "Self-evolve, learn, optimize, feedback and temperature tuning"
    proposed_changes = {"temperature": 0.15, "max_retries": 4}

    mutation = propose_mutation(
        agent_name="autobot",
        mutation_type=MutationType.PARAMETER_ADJUSTMENT,
        description=description,
        rationale="Current responses are too random for production tasks",
        proposed_changes=proposed_changes,
        expected_improvement=0.1,
        risk_level="medium",
    )

    assert mutation.description == description
    assert mutation.proposed_changes["temperature"] == 0.15
    assert mutation.mutation_id in engine.mutations
    assert engine.get_mutation(mutation.mutation_id).status == MutationStatus.IMPLEMENTED
    assert engine.get_mutation(mutation.mutation_id).mission_pillar is not None
    assert engine.get_mutation(mutation.mutation_id).quality_score is not None

    persisted = engine.get_mutation(mutation.mutation_id)
    _write_json(
        "01_proposed_mutation.json",
        {
            "mutation_id": persisted.mutation_id,
            "agent_name": persisted.agent_name,
            "mutation_type": persisted.mutation_type.value,
            "description": persisted.description,
            "rationale": persisted.rationale,
            "proposed_changes": persisted.proposed_changes,
            "expected_improvement": persisted.expected_improvement,
            "risk_level": persisted.risk_level,
            "mission_pillar": persisted.mission_pillar,
            "quality_score": persisted.quality_score,
            "status": persisted.status.value,
        },
    )

    _append_report(
        "1. Mutation Proposed and Implemented by Council",
        f"- **Mutation ID**: `{persisted.mutation_id}`\n"
        f"- **Agent**: {persisted.agent_name}\n"
        f"- **Description**: {persisted.description}\n"
        f"- **Proposed Changes**: {json.dumps(persisted.proposed_changes)}\n"
        f"- **Quality Score**: {persisted.quality_score}\n"
        f"- **Status**: {persisted.status.value}\n",
    )


def test_autonomous_mutation_cycle_consensus_and_approval() -> None:
    """Council reaches consensus, approves the mutation, and records the decision."""
    _clean_evidence()

    engine = get_evolution_engine()
    engine.mutations.clear()

    mutation = propose_mutation(
        agent_name="autobot",
        mutation_type=MutationType.PARAMETER_ADJUSTMENT,
        description="Self-evolve, learn, optimize, feedback and temperature tuning",
        rationale="Current responses are too random for deterministic tool use",
        proposed_changes={"temperature": 0.15, "max_retries": 4},
        expected_improvement=0.1,
        risk_level="medium",
    )

    persisted = engine.get_mutation(mutation.mutation_id)
    assert persisted is not None
    assert persisted.status == MutationStatus.IMPLEMENTED

    proposal_id = f"consensus-{mutation.mutation_id[:12]}"
    consensus = ConsensusEngine(agents=COUNCIL)
    consensus.create_proposal(
        proposal_id,
        mutation.agent_name,
        mutation.description,
        mutation.proposed_changes,
    )

    votes = {
        "autobot": ("approve", "Mutation improves determinism."),
        "alpha_evaluator": ("approve", "Risk is acceptable and testable."),
        "beta_worker": ("approve", "Aligned with mission pillar."),
    }
    for voter, (vote, reason) in votes.items():
        consensus.cast_vote(proposal_id, voter, vote, reason)

    consensus_result = consensus.check_consensus(proposal_id)
    assert consensus_result == "approved"

    approved = approve_mutation(mutation.mutation_id, approved_by="consensus")
    assert approved is True

    _write_json(
        "02_consensus_votes.json",
        {
            "proposal_id": proposal_id,
            "votes": {
                voter: {"vote": vote, "reason": reason}
                for voter, (vote, reason) in votes.items()
            },
            "consensus_result": consensus_result,
            "approved_by": "consensus",
            "final_status": engine.get_mutation(mutation.mutation_id).status.value,
        },
    )

    _append_report(
        "2. Consensus and Approval",
        f"- **Proposal ID**: `{proposal_id}`\n"
        f"- **Consensus Result**: {consensus_result}\n"
        f"- **Approval**: Approved by consensus\n"
        f"- **Final Status**: {engine.get_mutation(mutation.mutation_id).status.value}\n",
    )


def test_autonomous_mutation_cycle_implements_code_change_and_evidence() -> None:
    """
    Full autonomous cycle with a real file commit.

    This is the controlled test you can run and inspect afterwards.
    It leaves no permanent branch on failure and writes evidence artifacts.
    """
    _clean_evidence()
    _clean_git_branches()

    engine = get_evolution_engine()
    engine.mutations.clear()

    mutation = propose_mutation(
        agent_name="autobot",
        mutation_type=MutationType.BEHAVIOR_CHANGE,
        description="Self-evolve, optimize, feedback: add autonomous marker file",
        rationale="Controlled test of inline code mutation execution to prove autonomous improvement",
        proposed_changes={
            "file_changes": [
                {
                    "path": "evidence/autonomous_mutation_cycle/autonomous_marker.txt",
                    "kind": "add",
                    "content": "hello from autonomous mutation\n",
                }
            ],
            "commit_message": "test: add autonomous marker from council mutation",
        },
        expected_improvement=0.05,
        risk_level="low",
    )

    persisted = engine.get_mutation(mutation.mutation_id)
    assert persisted is not None
    assert persisted.status == MutationStatus.IMPLEMENTED

    result = implement_mutation(mutation.mutation_id)
    assert result.get("success") is True

    inner = result.get("result", {})
    assert inner.get("execution") == "code"
    assert inner.get("branch") == f"mutation/{mutation.mutation_id[:12]}"
    assert inner.get("promotion") == "committed"

    marker = EVIDENCE_DIR / "autonomous_marker.txt"
    assert marker.exists(), "Expected inline file mutation to write evidence artifact"
    assert marker.read_text(encoding="utf-8") == "hello from autonomous mutation\n"

    audit_events = read_audit_log()
    event_types = [event.get("event_type") for event in audit_events]
    assert "mutation_approved" in event_types
    assert "mutation_implemented" in event_types
    assert "code_mutation_committed" in event_types

    _write_json(
        "03_implementation_result.json",
        {
            "mutation_id": mutation.mutation_id,
            "final_status": persisted.status.value,
            "implementation": result,
            "marker_path": str(marker),
            "marker_content": marker.read_text(encoding="utf-8"),
            "audit_event_types": event_types,
        },
    )

    _append_report(
        "3. Autonomous Implementation",
        f"- **Mutation ID**: `{mutation.mutation_id}`\n"
        f"- **Git Branch**: `{inner.get('branch')}`\n"
        f"- **Changes Applied**: {json.dumps(inner.get('changes_applied'))}\n"
        f"- **Promotion**: {inner.get('promotion')}\n"
        f"- **Marker Path**: `{marker}`\n"
        f"- **Audit Events**: {', '.join(event_types[-5:])}\n"
        f"- **Push Output**: {inner.get('push')}\n",
    )
