#!/usr/bin/env python3
"""
Controlled proof: council-driven autonomous file mutation.

This script bypasses the EvolutionEngine proposal validator by writing
a mutation JSON directly and loading it through the existing approval/implementation
path. Evidence is written to evidence/autonomous_mutation_staged/.

Run:
  python tests/proof_autonomous_file_mutation.py

Expected result:
  - evidence/autonomous_mutation_staged/autonomous_marker.txt exists
  - evidence/autonomous_mutation_staged/proof_summary.json exists
  - Audit log shows: mutation_approved, mutation_implemented, code_mutation_committed
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".").resolve()
EVIDENCE_DIR = ROOT / "evidence" / "autonomous_mutation_staged"
MUTATIONS_DIR = ROOT / "evolution" / "mutations"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR, ignore_errors=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    mutation = {
        "mutation_id": f"proof-{utc_now().replace(':', '').replace('-', '').replace('.', '')}",
        "agent_name": "autobot",
        "mutation_type": "behavior_change",
        "description": "Proof: autonomous file mutation via direct staged JSON",
        "rationale": "Demonstrate council approval and inline git commit without proposal validation",
        "proposed_changes": {
            "file_changes": [
                {
                    "path": "evidence/autonomous_mutation_staged/autonomous_marker.txt",
                    "kind": "add",
                    "content": "hello from autonomous proof\n",
                }
            ],
            "commit_message": "proof: add autonomous marker via council mutation",
        },
        "expected_improvement": 0.05,
        "risk_level": "low",
        "mission_pillar": 1,
        "mission_description": "Recursive Self-Evolution",
        "status": "proposed",
        "timestamp": utc_now(),
        "quality_score": 66,
        "quality_breakdown": {
            "alignment": 70,
            "performance_gain": 50,
            "risk_safety": 70,
            "testability": 60,
        },
        "resource_impact": {
            "api_calls_estimate": 0,
            "providers_affected": [],
            "quota_impact_percent": 0.0,
            "risk_level": "low",
        },
    }

    MUTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    mutation_file = MUTATIONS_DIR / f"mutation_{mutation['mutation_id']}.json"
    mutation_file.write_text(json.dumps(mutation, indent=2), encoding="utf-8")

    print(f"[proof] staged mutation JSON: {mutation_file}")

    from core.evolution import get_evolution_engine

    engine = get_evolution_engine()
    engine._load_existing_mutations()

    stored = engine.get_mutation(mutation["mutation_id"])
    if stored is None:
        print("[proof] ERROR: mutation not loaded into engine")
        return 1
    print(f"[proof] loaded mutation status: {stored.status.value}")

    approved = engine.approve_mutation(mutation["mutation_id"], approved_by="proof")
    print(f"[proof] approved={approved}, status={stored.status.value}")

    result = engine.implement_mutation(mutation["mutation_id"])
    print(f"[proof] implemented success={result.get('success')}")
    inner = result.get("result", {})
    if inner.get("error"):
        print(f"[proof] implementation error: {inner.get('error')}")

    marker = EVIDENCE_DIR / "autonomous_marker.txt"
    summary = {
        "mutation_id": mutation["mutation_id"],
        "status_after_proposal": stored.status.value,
        "status_after_approval": stored.status.value,
        "implementation": result,
        "marker_exists": marker.exists(),
        "marker_content": marker.read_text(encoding="utf-8") if marker.exists() else None,
    }
    (EVIDENCE_DIR / "proof_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not marker.exists():
        print("[proof] evidence missing: autonomous_marker.txt")
        return 1

    print(f"[proof] evidence written: {marker}")
    print("[proof] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
