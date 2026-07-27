#!/usr/bin/env python3
"""Evidence: Step 5 allowlisted file mutation proposal."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from core.evolution import get_evolution_engine, MutationType

engine = get_evolution_engine()
engine.mutations.clear()

mutation = engine.propose_mutation(
    agent_name="autobot",
    mutation_type=MutationType.BEHAVIOR_CHANGE,
    description="Self-evolve, optimize, feedback, mutation, evolution: allowlisted file change in agents/",
    rationale="Step 5 proof: file mutation via allowlisted path with council votes",
    proposed_changes={
        "file_changes": [
            {
                "path": "agents/autobot.py",
                "kind": "edit",
                "content": "# Step 5 allowlist proof\n"
            }
        ],
        "commit_message": "step5: allowlisted file mutation proof",
    },
    expected_improvement=0.05,
    risk_level="low",
)

Path("evidence/step5_allowlist_evidence.json").write_text(
    json.dumps(
        {
            "mutation_id": mutation.mutation_id,
            "status": mutation.status.value,
            "rollout_state": mutation.rollout_state,
            "proposed_changes_keys": list(mutation.proposed_changes.keys()),
        },
        indent=2,
    ),
    encoding="utf-8",
)

print(f"Status: {mutation.status.value}")
print(f"Rollout state: {mutation.rollout_state}")
print("Evidence written to evidence/step5_allowlist_evidence.json")
