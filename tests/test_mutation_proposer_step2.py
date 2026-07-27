#!/usr/bin/env python3
"""Evidence: two different performance inputs produce different proposer outputs."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from core.mutation_proposer import propose_mutation


async def main():
    low_perf = {
        "success_rate": 0.15,
        "avg_latency": 4.2,
        "error_rate": 0.6,
        "score": 0.2,
    }
    high_perf = {
        "success_rate": 0.92,
        "avg_latency": 0.8,
        "error_rate": 0.05,
        "score": 0.9,
    }

    out_low = await propose_mutation("autobot", low_perf, ["failed tool call", "timeout"])
    out_high = await propose_mutation("autobot", high_perf, ["successful execution"])

    print("LOW PERF PROPOSAL:")
    print(json.dumps(out_low, indent=2))
    print("\nHIGH PERF PROPOSAL:")
    print(json.dumps(out_high, indent=2))

    summary = {
        "low_perf_input": low_perf,
        "high_perf_input": high_perf,
        "low_perf_output": out_low,
        "high_perf_output": out_high,
        "different": out_low != out_high,
    }
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/step2_proposer_evidence.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("\nEvidence written to evidence/step2_proposer_evidence.json")


if __name__ == "__main__":
    asyncio.run(main())
