#!/usr/bin/env python3
"""Evidence: real council votes produce distinct reasons for medium-risk mutation."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from core.evolution import get_evolution_engine, MutationType, MutationStatus

engine = get_evolution_engine()
engine.mutations.clear()

mutation = engine.propose_mutation(
    agent_name="autobot",
    mutation_type=MutationType.PARAMETER_ADJUSTMENT,
    description="Self-evolve, optimize, feedback: medium-risk parameter tuning with council vote",
    rationale="Medium-risk change requires real council votes to proceed",
    proposed_changes={"max_retries": 4},
    expected_improvement=0.1,
    risk_level="medium",
)

if mutation.status != MutationStatus.PENDING_APPROVAL:
    print(f"FAIL: expected pending approval, got {mutation.status.value}")
    sys.exit(1)

print(f"Mutation {mutation.mutation_id} is pending approval")

result = asyncio.run(engine.collect_council_votes(mutation.mutation_id))
votes = result.get("votes", {})
reasons = [v.get("reason", "") for v in votes.values() if v.get("reason")]
distinct = len(set(reasons)) >= 3

Path("evidence").mkdir(exist_ok=True)
Path("evidence/step3_vote_evidence.json").write_text(
    json.dumps(
        {
            "mutation_id": mutation.mutation_id,
            "status": mutation.status.value,
            "result": result,
            "distinct_reasons": distinct,
            "vote_reasons": reasons,
        },
        indent=2,
    ),
    encoding="utf-8",
)

print(f"Votes: {json.dumps(votes, indent=2)}")
print(f"Distinct reasons: {distinct}")
print("Evidence written to evidence/step3_vote_evidence.json")
sys.exit(0 if distinct else 1)
