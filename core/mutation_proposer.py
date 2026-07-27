"""Propose config mutations from performance + trajectory data."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

VALID_PARAMS = {
    "autobot": ["temperature", "max_retries", "system_prompt"],
    "alpha_evaluator": ["temperature", "system_prompt"],
    "beta_worker": ["temperature", "system_prompt"],
}

FALLBACK_MUTATIONS = {
    "autobot": {"temperature": 0.15, "max_retries": 4},
    "alpha_evaluator": {"temperature": 0.15},
    "beta_worker": {"temperature": 0.15},
}

PROMPT_TEMPLATE = """\
You are the Mutation Proposer for agent `{agent_name}`.

Mission context:
- Pillar 1: Recursive Self-Evolution
- Pillar 2: Autonomous Resource Optimization
- Pillar 3: Model Agnosticism
- Pillar 4: Durable Local State
- Pillar 5: Companion Alignment

Recent performance:
{performance_text}

Recent trajectories (recent tool invocations):
{trajectory_text}

Return JSON only:
{{
  "mutation_type": "parameter_adjustment" | "prompt_optimization" | "strategy_evolution",
  "description": "short description of the proposed change",
  "rationale": "why this change is expected to help",
  "proposed_changes": {{"temperature": 0.2, "max_retries": 5}},
  "risk_level": "low" | "medium" | "high",
  "expected_improvement": 0.1
}}

Rules:
- `proposed_changes` keys must be one of: {valid_params}
- Do not propose keys outside that set
- If uncertain, choose low-risk parameter_adjustment
- `expected_improvement` is 0.0-1.0
"""


def _format_performance(performance: Dict[str, Any]) -> str:
    lines = []
    for key in ["success_rate", "avg_latency", "error_rate", "score", "evaluation_score"]:
        if key in performance:
            lines.append(f"- {key}: {performance[key]}")
    return "\n".join(lines) if lines else "- no explicit metrics provided"


def _format_trajectories(trajectories: Optional[List[str]]) -> str:
    if not trajectories:
        return "- no recent trajectories provided"
    lines = []
    for item in trajectories[-8:]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _safe_fallback(agent_name: str) -> Dict[str, Any]:
    return {
        "mutation_type": "parameter_adjustment",
        "description": "Safe fallback parameter tuning",
        "rationale": "Proposer unavailable; applying conservative defaults",
        "proposed_changes": FALLBACK_MUTATIONS.get(agent_name, {"temperature": 0.15}).copy(),
        "risk_level": "low",
        "expected_improvement": 0.05,
    }


async def propose_mutation(
    agent_name: str,
    performance: Dict[str, Any],
    recent_trajectories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate a config mutation proposal from current performance state."""

    valid_params = VALID_PARAMS.get(agent_name, ["temperature"])
    prompt = PROMPT_TEMPLATE.format(
        agent_name=agent_name,
        performance_text=_format_performance(performance),
        trajectory_text=_format_trajectories(recent_trajectories),
        valid_params=", ".join(valid_params),
    )

    try:
        from core.api_router import get_llm_router

        router = get_llm_router()
        response = await router.route_request(
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
        proposal = json.loads(content)

        if not isinstance(proposal, dict):
            raise ValueError("Proposer returned non-dict JSON")

        proposal.setdefault("mutation_type", "parameter_adjustment")
        proposal.setdefault("description", "Auto-generated tuning")
        proposal.setdefault("rationale", "Performance-based proposer output")
        proposal.setdefault("risk_level", "medium")
        proposal.setdefault("expected_improvement", 0.1)

        changes = proposal.get("proposed_changes") or {}
        if not isinstance(changes, dict):
            changes = {}

        filtered = {k: v for k, v in changes.items() if k in valid_params}
        if not filtered:
            filtered = FALLBACK_MUTATIONS.get(agent_name, {"temperature": 0.15}).copy()
        proposal["proposed_changes"] = filtered

        try:
            proposal["mutation_type"] = proposal["mutation_type"].lower().replace(" ", "_")
        except Exception:
            proposal["mutation_type"] = "parameter_adjustment"

        return proposal

    except Exception as exc:
        print(f"[MUTATION PROPOSER] Fallback due to: {exc}")
        return _safe_fallback(agent_name)
