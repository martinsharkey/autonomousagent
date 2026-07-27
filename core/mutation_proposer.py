"""Propose config mutations from performance + trajectory data."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

VALID_PARAMS = {
    "autobot": ["max_retries", "system_prompt"],
    "alpha_evaluator": ["system_prompt"],
    "beta_worker": ["max_retries", "system_prompt"],
}

FALLBACK_MUTATIONS = {
    "autobot": {"temperature": 0.15, "max_retries": 4},
    "alpha_evaluator": {"temperature": 0.15},
    "beta_worker": {"temperature": 0.15},
}

RECENT_PROPOSALS_MAX = 8

FILE_MUTATION_ALLOWLIST = [
    "agents/",
    "core/",
    "governance/",
    "tools/",
    "microbots/",
    "tests/",
    "providers.yaml",
    "README.md",
    "MISSION_PURPOSE.md",
    "MUTATIONS_ROADMAP.md",
    "TODO.md",
    "session_log.md",
]

FILE_MUTATION_DENYLIST = [
    ".env",
    ".git",
    "secrets/",
    "autonomous_loops/",
]

PROMPT_TEMPLATE = """\
You are the Mutation Proposer for agent `{agent_name}`.

Mission context:
- Pillar 1: Recursive Self-Evolution
- Pillar 2: Autonomous Resource Optimization
- Pillar 3: Model Agnosticism
- Pillar 4: Durable Local State
- Pillar 5: Companion Alignment

Your job is to propose changes that make the council more capable, broader, and more autonomous.
Prefer proposals that:
- Add real capabilities: web scraping, research, tool use, file editing, provider expansion
- Improve code quality, resilience, or observability
- Reduce reliance on any single provider
- Close real gaps in the system
- Do NOT propose secrets, .env changes, or destructive system changes

Recent performance:
{performance_text}

Recent trajectories (recent tool invocations):
{trajectory_text}

Recent proposals (avoid repeating these):
{recent_proposals_text}

Return JSON only:
{{
  "mutation_type": "parameter_adjustment" | "prompt_optimization" | "strategy_evolution" | "tool_addition",
  "description": "short description of the proposed change",
  "rationale": "why this change is expected to help",
  "proposed_changes": {{"file_changes": [{{"path": "core/web_scraper.py", "kind": "create", "content": "..."}}]}},
  "risk_level": "low" | "medium" | "high",
  "expected_improvement": 0.1
}}

Rules:
- `proposed_changes` can be config params OR file changes
- Valid config params for this agent: {valid_params}
- File changes are allowed ONLY in these paths:
  - agents/*.py
  - core/*.py
  - governance/*.py
  - tools/*.py
  - microbots/*.py
  - tests/*.py
  - providers.yaml
  - MISSION_PURPOSE.md
  - MUTATIONS_ROADMAP.md
  - TODO.md
  - session_log.md
  - README.md
- File changes format:
  {{"file_changes": [{{"path": "core/web_scraper.py", "kind": "create", "content": "..."}}]}}
- You may also include `commit_message` for file changes
- Do NOT propose changes to .env, .git, or secrets/
- STRONGLY PREFER file/tool mutations over parameter tweaks
- Prefer adding new capabilities or improving architecture over parameter tuning
- ONLY propose parameter_adjustment if there is concrete evidence a specific parameter change fixes a measured problem
- If no meaningful change is apparent, return {{"proposed_changes": {{}}}} and the system will skip this cycle
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


def _format_recent_proposals(recent_proposals: Optional[List[Dict[str, Any]]]) -> str:
    if not recent_proposals:
        return "- no recent proposals"
    lines = []
    for item in recent_proposals[-RECENT_PROPOSALS_MAX:]:
        desc = item.get("description", "")
        changes = item.get("proposed_changes", {})
        lines.append(f"- {desc} | {json.dumps(changes)[:120]}")
    return "\n".join(lines)


def _safe_fallback(agent_name: str) -> Optional[Dict[str, Any]]:
    return None


async def propose_mutation(
    agent_name: str,
    performance: Dict[str, Any],
    recent_trajectories: Optional[List[str]] = None,
    recent_proposals: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Generate a config mutation proposal from current performance state.
    
    Returns None if no meaningful proposal can be generated.
    """
    valid_params = VALID_PARAMS.get(agent_name, ["temperature"])
    prompt = PROMPT_TEMPLATE.format(
        agent_name=agent_name,
        performance_text=_format_performance(performance),
        trajectory_text=_format_trajectories(recent_trajectories),
        recent_proposals_text=_format_recent_proposals(recent_proposals),
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

        if not changes:
            return None

        file_changes_data = changes.get("file_changes")
        if isinstance(file_changes_data, list) and file_changes_data:
            proposal["proposed_changes"] = changes
        else:
            filtered = {k: v for k, v in changes.items() if k in valid_params}
            if not filtered:
                return None
            proposal["proposed_changes"] = filtered

        try:
            proposal["mutation_type"] = proposal["mutation_type"].lower().replace(" ", "_")
        except Exception:
            proposal["mutation_type"] = "parameter_adjustment"

        return proposal

    except Exception as exc:
        print(f"[MUTATION PROPOSER] Fallback due to: {exc}")
        return _safe_fallback(agent_name)


class MutationProposer:
    def __init__(self):
        self.recent_proposals: List[Dict[str, Any]] = []

    def record_proposal(self, proposal: Dict[str, Any]):
        if proposal:
            self.recent_proposals.append(proposal)
            if len(self.recent_proposals) > RECENT_PROPOSALS_MAX:
                self.recent_proposals = self.recent_proposals[-RECENT_PROPOSALS_MAX:]

    def get_recent_proposals(self) -> List[Dict[str, Any]]:
        return list(self.recent_proposals)
