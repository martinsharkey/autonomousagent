"""Propose mutations from performance + trajectory data."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

VALID_PARAMS = {
    "autobot": ["max_retries", "system_prompt"],
    "alpha_evaluator": ["system_prompt"],
    "beta_worker": ["max_retries", "system_prompt"],
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

PILLAR_GUIDANCE = {
    1: "Propose improvements to error handling, failure recovery, learning mechanisms, feedback loops",
    2: "Propose quota optimization, provider switching, request caching, batch processing",
    3: "Propose new provider support, improved failover, multi-provider testing",
    4: "Propose state management improvements, checkpoint verification, recovery procedures",
    5: "Propose Telegram improvements, natural language support, status reporting",
}

MISSION_PILLARS = {
    1: "Recursive Self-Evolution",
    2: "Autonomous Resource Optimization",
    3: "Model Agnosticism",
    4: "Durable Local State",
    5: "Companion Alignment",
}

CURRENT_PILLAR_FILE = "evolution/current_pillar.txt"


def _load_current_pillar() -> int:
    try:
        with open(CURRENT_PILLAR_FILE, "r") as f:
            val = f.read().strip()
            return int(val)
    except Exception:
        return 1


def _save_current_pillar(pillar: int) -> None:
    try:
        from pathlib import Path
        Path("evolution").mkdir(parents=True, exist_ok=True)
        with open(CURRENT_PILLAR_FILE, "w") as f:
            f.write(str(((pillar % 5) + 5) % 5 or 5))
    except Exception:
        pass


async def select_mission_pillar() -> int:
    current = _load_current_pillar()
    next_pillar = (current % 5) + 1
    _save_current_pillar(next_pillar)
    return next_pillar


PROMPT_TEMPLATE = """\
You are the Mutation Proposer for agent `{agent_name}`.

MISSION PILLARS:
- Pillar 1: Recursive Self-Evolution - improve ability to learn and adapt
- Pillar 2: Autonomous Resource Optimization - reduce costs and optimize free tier usage
- Pillar 3: Model Agnosticism - support multiple LLM providers
- Pillar 4: Durable Local State - improve persistence and recovery
- Pillar 5: Companion Alignment - improve human-council communication

CURRENT FOCUS PILLAR: Pillar {current_mission_pillar} - {pillar_name}

Your job: Propose mutations that ADVANCE Pillar {current_mission_pillar}

For Pillar {current_mission_pillar}, consider:
{pillar_guidance}

Recent performance:
{performance_text}

Recent trajectories (recent tool invocations):
{trajectory_text}

Recent proposals (avoid repeating these):
{recent_proposals_text}

Council discussion context:
{council_discussion}

Learning from past mutations:
{learned_context}

Existing architecture (do NOT duplicate these):
{existing_architecture}

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
- For config params, put the parameter name directly inside `proposed_changes`
- For example: `"proposed_changes": {{"max_retries": 5}}` or `"proposed_changes": {{"system_prompt": "new prompt text"}}`
- Do NOT use `params` as the key; use the actual parameter name directly inside `proposed_changes`

Rules:
- MISSION FILES ONLY: propose changes ONLY in these paths:
  - agents/*.py
  - tools/*.py
  - governance/*.py
  - microbots/*.py
  - tests/*.py
  - providers.yaml
  - MISSION_PURPOSE.md
  - MUTATIONS_ROADMAP.md
  - TODO.md
  - session_log.md
  - README.md
  - core/goals.py
  - core/health.py
  - core/learning.py
  - core/feedback.py
  - core/memory.py
  - core/evaluation.py
  - core/governor.py
  - core/heartbeat.py
  - core/error_handler.py
  - core/escalation_handler.py
  - core/autonomy_levels.py
  - core/llm_cache.py
  - core/llm_provider.py
  - core/provider_router.py
  - core/quota_monitor.py
  - core/sandbox.py
  - core/state_manager.py
  - core/state_recovery.py
  - core/ollama_client.py
  - core/temperature_selector.py
  - core/tool_discovery.py
  - core/deployer.py
  - core/council_monitor.py
  - core/data_logger.py
  - core/operator_interface.py
  - core/provider_benchmark.py
  - core/react.py
  - core/recovery.py
  - core/rollout.py
  - core/mesh_communication.py
  - core/node_monitor.py
  - core/semantic_cache.py
  - core/code_mode.py
  - core/agent_context.py
  - core/agent_communication_enhanced.py
  - core/version_store.py
  - core/snapdeploy.py
  - tools/evolution_analyzer.py
  - tools/provider_health_probe.py
  - tools/request_cache.py
  - tools/web_researcher.py
  - tools/telegram_status.py
  - tools/mutation_tracker.py
  - tools/ollama_adapter.py
  - tools/mcp_server.py
  - tools/tool_catalogue_mcp.py
- FORBIDDEN: Do NOT propose changes to these critical files:
  - core/agent_loop.py
  - core/api_router.py
  - core/evolution.py
  - core/telegram.py
  - council_daemon.py
  - core/state.py
  - core/graph.py
  - core/rollback.py
  - core/snapshots.py
  - core/checkpointer.py
  - core/planning.py
  - core/curiosity.py
  - core/communication.py
- The critical file list OVERRIDES any other allowance
- File changes format:
    {{"file_changes": [{{"path": "tools/new_tool.py", "kind": "create", "content": "..."}}]}}
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
  - CRITICAL: Do NOT propose changes to these core infrastructure files:
    - core/agent_loop.py
    - core/api_router.py
    - core/evolution.py
    - core/telegram.py
    - council_daemon.py
    - core/state.py
    - core/graph.py
    - core/rollback.py
    - core/snapshots.py
    - core/checkpointer.py
    - core/planning.py
    - core/curiosity.py
    - core/communication.py
  - File changes format:
    {{"file_changes": [{{"path": "tools/new_tool.py", "kind": "create", "content": "..."}}]}}
- You may also include `commit_message` for file changes
- Do NOT propose changes to .env, .git, or secrets/
- STRONGLY PREFER file/tool/architecture mutations over parameter tweaks for non-trivial improvements
- ONLY propose parameter_adjustment if there is concrete evidence a specific parameter change fixes a measured problem AND the value is not already active
- If the only honest proposal is parameter_adjustment, return {{"proposed_changes": {{}}}} and the system will skip this cycle
- `expected_improvement` is 0.0-1.0
- Do NOT propose temperature changes; temperature is managed by the LLM router/call path
- Map your proposal to a mission pillar; if none apply, skip by returning empty proposed_changes
- Mission pillars:
  1) Recursive self-evolution
  2) Autonomous resource optimization
  3) Model agnosticism
  4) Durable local state
  5) Companion alignment
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


def _load_existing_architecture() -> str:
    """Return a concise inventory of existing core modules/components."""
    modules = [
        "core/telegram.py - Telegram bot + command listener",
        "core/evolution.py - Mutation engine with council votes",
        "core/agent_loop.py - Autonomous agent loop",
        "core/curiosity.py - Curiosity scoring",
        "core/feedback.py - Feedback loop",
        "core/learning.py - Pattern extraction and recommendations",
        "core/goals.py - Goal store (SQLite)",
        "core/agent_config.py - Versioned agent config store",
        "core/health.py - Health checks",
        "core/api_router.py - LLM provider router",
        "core/planning.py - Agent planner with tool use",
        "core/sandbox.py - Sandbox execution",
        "core/model_check.py - Model preflight checks",
        "core/checkpointer.py - Durable state checkpointer",
        "tools/mcp_registry.py - Tool registry",
        "tools/code_validator.py - AST-based static analyzer",
        "tools/provider_optimizer.py - Provider fallback/caching",
        "governance/audit_log.py - HMAC audit log",
        "governance/consensus.py - Council consensus engine",
        "governance/zero_trust.py - Zero-trust messaging",
        "governance/keys.py - Key management + rotation",
        "governance/rotate_keys.py - Key rotation CLI",
    ]
    return "Existing architecture (do NOT duplicate these):\n" + "\n".join(f"- {m}" for m in modules)


def _build_learning_context(agent_name: str) -> str:
    try:
        from core.evolution import get_evolution_engine

        engine = get_evolution_engine()
        promoted = engine.get_promoted_mutations(agent_name, limit=3)
        failed = engine.get_failed_mutations(agent_name, limit=3)

        context = "## What Worked (Promoted Mutations):\n"
        if promoted:
            for m in promoted:
                improvement = (
                    m.implementation_result.get("improvement")
                    if isinstance(m.implementation_result, dict)
                    else None
                )
                context += f"✅ {m.description}"
                if improvement:
                    context += f" — improvement: {improvement}"
                context += "\n"
        else:
            context += "- no promoted mutations yet\n"

        context += "\n## What Failed (Rolled Back / Failed):\n"
        if failed:
            for m in failed:
                reason = (
                    m.implementation_result.get("reason_rollback")
                    if isinstance(m.implementation_result, dict)
                    else str(m.implementation_result)
                )
                context += f"❌ {m.description}: {reason}\n"
        else:
            context += "- no failed mutations yet\n"

        return context
    except Exception:
        return "- unable to load learning context"


async def propose_mutation(
    agent_name: str,
    performance: Dict[str, Any],
    recent_trajectories: Optional[List[str]] = None,
    recent_proposals: Optional[List[Dict[str, Any]]] = None,
    mission_pillar: Optional[int] = None,
    council_discussion: Optional[str] = None,
    learned_context: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Generate a mutation proposal from current performance state.

    Args:
        agent_name: Agent proposing.
        performance: Current metrics.
        recent_trajectories: Recent tool invocations.
        recent_proposals: Recent proposals to avoid repeating.
        mission_pillar: Current mission pillar focus.
        council_discussion: Summary of prior agent discussion.

    Returns:
        Proposal dict or None if no meaningful proposal.
    """
    if mission_pillar is None:
        mission_pillar = await select_mission_pillar()

    pillar_name = MISSION_PILLARS.get(mission_pillar, "Unknown")
    pillar_guidance = PILLAR_GUIDANCE.get(mission_pillar, "")

    valid_params = VALID_PARAMS.get(agent_name, [])

    prompt = PROMPT_TEMPLATE.format(
        agent_name=agent_name,
        performance_text=_format_performance(performance),
        trajectory_text=_format_trajectories(recent_trajectories),
        recent_proposals_text=_format_recent_proposals(recent_proposals),
        valid_params=", ".join(valid_params),
        current_mission_pillar=mission_pillar,
        pillar_name=pillar_name,
        pillar_guidance=pillar_guidance,
        council_discussion=council_discussion or "- no prior discussion",
        learned_context=learned_context or "- no past mutation history",
        existing_architecture=_load_existing_architecture(),
    )

    proposal = None
    try:
        from core.api_router import get_llm_router

        router = get_llm_router()
        response = await router.route_request(
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
        start = content.find("{")
        proposal = None
        if start >= 0:
            try:
                proposal, _ = json.JSONDecoder().raw_decode(content[start:])
            except Exception:
                proposal = None
        if proposal is None:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    proposal = json.loads(match.group())
                except Exception:
                    proposal = None
        if proposal is None:
            raise ValueError("Proposer returned invalid JSON")

        if not isinstance(proposal, dict):
            raise ValueError("Proposer returned non-dict JSON")

        proposal.setdefault("mutation_type", "parameter_adjustment")
        proposal.setdefault("description", "Auto-generated tuning")
        proposal.setdefault("rationale", "Performance-based proposer output")
        proposal.setdefault("risk_level", "medium")
        proposal.setdefault("expected_improvement", 0.1)
        proposal.setdefault("mission_pillar", mission_pillar)
        proposal.setdefault("agent_name", agent_name)

        changes = proposal.get("proposed_changes") or {}
        if not isinstance(changes, dict):
            changes = {}

        if not changes and "params" in proposal:
            changes = proposal.get("params") or {}
            if isinstance(changes, dict):
                proposal["proposed_changes"] = changes

        if not changes:
            return None

        file_changes_data = changes.get("file_changes")
        if isinstance(file_changes_data, list) and file_changes_data:
            valid_file_changes = []
            for fc in file_changes_data:
                if not isinstance(fc, dict):
                    continue
                fc_path = fc.get("path", "")
                denied = any(fc_path.startswith(d) for d in FILE_MUTATION_DENYLIST)
                if denied:
                    continue
                allowed = any(fc_path.startswith(a) or fc_path == a for a in FILE_MUTATION_ALLOWLIST)
                if not allowed:
                    continue
                valid_file_changes.append(fc)
            if valid_file_changes:
                proposal["proposed_changes"] = {"file_changes": valid_file_changes}
            else:
                return None
        else:
            filtered = {k: v for k, v in changes.items() if k in valid_params}
            if not filtered:
                return None
            proposal["proposed_changes"] = filtered
            return None

        try:
            proposal["mutation_type"] = proposal["mutation_type"].lower().replace(" ", "_")
        except Exception:
            proposal["mutation_type"] = "parameter_adjustment"

        try:
            from core.mutation_validator import MutationValidator

            validator = MutationValidator()
            is_valid, reason = await validator.validate_proposal(proposal)
            if not is_valid:
                print(f"[PROPOSER] Rejected invalid mutation: {reason}")
                return None
        except Exception as exc:
            print(f"[PROPOSER] Validation error: {exc}")

        try:
            from core.mutation_deduplicator import get_deduplicator
            dedup = get_deduplicator()
            dedup_proposal = {
                "agent_name": agent_name,
                "mutation_type": proposal.get("mutation_type", "parameter_adjustment"),
                "description": proposal.get("description", ""),
                "proposed_changes": proposal.get("proposed_changes", {}),
            }
            should_propose = dedup.should_propose(dedup_proposal)
            if not should_propose:
                return None
        except Exception:
            pass

        return proposal
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"[MUTATION PROPOSER] Fallback due to: {exc}")
        return None


class MutationProposer:
    def __init__(self):
        self.recent_proposals: List[Dict[str, Any]] = []

    def record_proposal(self, proposal: Dict[str, Any]):
        if proposal:
            self.recent_proposals.append(proposal)
            if len(self.recent_proposals) > RECENT_PROPOSALS_MAX:
                self.recent_proposals = self.recent_proposals[-RECENT_PROPOSALS_MAX:]
            try:
                from core.mutation_deduplicator import get_deduplicator
                get_deduplicator().record_proposed(proposal)
            except Exception:
                pass

    def get_recent_proposals(self) -> List[Dict[str, Any]]:
        return list(self.recent_proposals)
