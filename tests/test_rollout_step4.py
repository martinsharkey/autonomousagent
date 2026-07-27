#!/usr/bin/env python3
"""Evidence: canary -> fleet rollout for config mutation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from core.evolution import get_evolution_engine, propose_mutation, approve_mutation, implement_mutation, MutationType
from core.rollout import start_canary, advance_rollout, rollout_status

engine = get_evolution_engine()
engine.mutations.clear()

mutation = propose_mutation(
    agent_name="autobot",
    mutation_type=MutationType.PARAMETER_ADJUSTMENT,
    description="Self-evolve, optimize, feedback: canary then fleet rollout test",
    rationale="Prove config rollout across fleet with eval gate",
    proposed_changes={"temperature": 0.15, "max_retries": 4},
    expected_improvement=0.1,
    risk_level="low",
)

approve_mutation(mutation.mutation_id, approved_by="step4_test")
implement_mutation(mutation.mutation_id)

canary = start_canary(mutation.mutation_id)
fleet_rollout = advance_rollout(mutation.mutation_id)
status = rollout_status(mutation.mutation_id)

Path("evidence").mkdir(exist_ok=True)
Path("evidence/step4_rollout_evidence.json").write_text(
    json.dumps(
        {
            "mutation_id": mutation.mutation_id,
            "canary": canary,
            "fleet_rollout": fleet_rollout,
            "rollout_status": status,
        },
        indent=2,
    ),
    encoding="utf-8",
)

print(json.dumps({"canary": canary, "fleet": fleet_rollout, "status": status}, indent=2))
print("Evidence written to evidence/step4_rollout_evidence.json")
