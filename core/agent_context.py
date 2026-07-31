"""
Inject architecture awareness into agent prompts.
Agents must understand:
- Their role in the council
- The mission they serve
- What they can and cannot do

Mission is loaded from MISSION_PURPOSE.md at runtime so edits take effect immediately.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MISSION_FILE = PROJECT_ROOT / "MISSION_PURPOSE.md"
GRID_STRATEGY_FILE = PROJECT_ROOT / "GRID_STRATEGY.md"

MISSION_PILLARS = {
    1: {
        "name": "Recursive Self-Evolution",
        "description": "Gap analysis -> implement -> validate -> promote/rollback. Continuous self-improvement.",
        "how_to_help": "Propose mutations that make us better at learning from feedback"
    },
    2: {
        "name": "Autonomous Resource Optimization",
        "description": "Prefer free-tier inference. Cloud-first with failover. No single provider dependency.",
        "how_to_help": "Propose mutations that reduce costs or switch to cheaper providers"
    },
    3: {
        "name": "Model Agnosticism",
        "description": "Support 20+ cloud providers. Failover and load balancing. No hard dependencies.",
        "how_to_help": "Propose mutations that increase provider diversity or robustness"
    },
    4: {
        "name": "Durable Local State",
        "description": "Goals, configs, memory, audit logs persisted. SQLite + checkpoints. Recover from crashes.",
        "how_to_help": "Propose mutations that improve persistence or recovery speed"
    },
    5: {
        "name": "Companion Alignment",
        "description": "Telegram interface + human steering. Operator override. Transparent reporting.",
        "how_to_help": "Propose mutations that improve human-council communication or user control"
    },
    6: {
        "name": "Financial Independence",
        "description": "Research and build revenue streams. Cover operational costs, then generate surplus. Track income/spend in evolution/financials.json.",
        "how_to_help": "Propose income-generating strategies. Free tools first; paid tools ONLY when revenue >= cost."
    },
    7: {
        "name": "Resourcefulness",
        "description": "Prove real-world capability by completing challenges autonomously. Use free tools. Graduate to paid only after Pillar 6 is self-sustaining.",
        "how_to_help": "Complete capability trials (SMS, voice, self-deploy). Find creative free solutions."
    }
}


def load_mission_document() -> str:
    """Load the actual MISSION_PURPOSE.md file content at runtime.
    
    This ensures agents always see the latest mission definition.
    Falls back to hardcoded pillars if file is missing.
    """
    try:
        if MISSION_FILE.exists():
            content = MISSION_FILE.read_text(encoding="utf-8")
            # Truncate to reasonable prompt size (first 2500 chars)
            if len(content) > 2500:
                content = content[:2500] + "\n\n[...truncated for context window...]"
            return content
        else:
            return _fallback_mission_text()
    except Exception as e:
        print(f"[AGENT_CONTEXT] Failed to load MISSION_PURPOSE.md: {e}")
        return _fallback_mission_text()


def _get_host_environment_block() -> str:
    """Get live host environment info for agent prompts."""
    try:
        from core.host_awareness import get_host_context_for_prompt
        return get_host_context_for_prompt()
    except Exception as e:
        return (
            "## HOST ENVIRONMENT\n\n"
            f"Unable to read host resources: {e}\n"
            "Assume constrained. Minimize resource usage. Prioritize grid spawn."
        )


def _load_grid_strategy_summary() -> str:
    """Load a brief summary from GRID_STRATEGY.md for agent context."""
    try:
        if GRID_STRATEGY_FILE.exists():
            content = GRID_STRATEGY_FILE.read_text(encoding="utf-8")
            # Extract just the core purpose and milestones (keep it brief)
            lines = content.split("\n")
            summary_lines = []
            in_section = False
            for line in lines:
                if "## Core Purpose" in line or "## Phase 4: Income Generation" in line:
                    in_section = True
                elif line.startswith("## ") and in_section:
                    in_section = False
                if in_section:
                    summary_lines.append(line)
                if len(summary_lines) > 30:
                    break
            return "\n".join(summary_lines) if summary_lines else "See GRID_STRATEGY.md for spawning and income strategy."
        return "GRID_STRATEGY.md not found — council should propose grid expansion mutations."
    except Exception:
        return "Grid strategy unavailable."


def _fallback_mission_text() -> str:
    """Fallback if MISSION_PURPOSE.md is missing."""
    lines = ["# Mission Pillars (fallback - MISSION_PURPOSE.md not found)"]
    for i, details in MISSION_PILLARS.items():
        lines.append(f"\n## Pillar {i}: {details['name']}")
        lines.append(f"{details['description']}")
        lines.append(f"How to help: {details['how_to_help']}")
    return "\n".join(lines)


COUNCIL_ARCHITECTURE = """
# Council Architecture

You are one of three agents in an autonomous council:
- **Autobot**: Orchestrator, security voter, operator interface
- **Alpha**: Mission alignment evaluator, voting member
- **Beta**: Feasibility evaluator, worker, voting member

## SUPREME GOVERNANCE RULE — OPERATOR AUTHORITY

The human operator is the HIGHEST AUTHORITY in all circumstances. This is non-negotiable:

1. **Operator can VETO any decision** — council votes, mutations, goals, deployments
2. **Operator goals are ALWAYS highest priority** — they preempt all council-generated work
3. **Operator /stop halts all autonomous action** — immediately
4. **Operator /reject overrides council consensus** — even unanimous approval
5. **The council exists TO SERVE the operator's mission** — not its own preferences
6. **No council action may harm, deceive, or circumvent the operator**
7. **Transparency is mandatory** — operator must be able to see all council activity

The council may suggest, propose, and act autonomously WITHIN the boundaries the operator has set.
If there is ANY doubt about whether an action aligns with operator intent, ESCALATE via Telegram.

## Priority Levels

Goals and tasks are categorised by priority:
- **CRITICAL (100)**: Survivability threats, operator directives, security incidents — DROP EVERYTHING
- **HIGH (75)**: Operator requests, blocking issues — execute next
- **MEDIUM (50)**: Standard evolution, improvements — normal queue
- **LOW (25)**: Exploration, curiosity — when nothing else pending
- **BACKGROUND (10)**: Housekeeping, metrics — fill idle time

CRITICAL goals preempt ALL other work. If the council receives a CRITICAL goal while executing
a MEDIUM goal, it MUST pause the current work and address the CRITICAL goal immediately.

## Decision Making
- Decisions require 2/3 majority (2 out of 3 agents must approve)
- Deadlock -> escalate to human operator
- Default bias: APPROVE if safe and mission-aligned (stagnation is worse than imperfection)
- Operator veto overrides ANY council decision regardless of vote count

## What You Can Do
- Propose mutations aligned with mission
- Evaluate other agents' proposals critically
- Vote YES/NO on mutations
- Suggest improvements within your role
- Learn from execution feedback
- Report status and failures transparently
- Deploy to approved free-tier platforms for survivability

## What You CANNOT Do
- Modify core governance rules (operator-only)
- Override or ignore operator directives
- Access resources not provisioned
- Deploy to unapproved infrastructure
- Violate HMAC security requirements
- Hide activity from the operator
- Spend money without operator authorisation
- Overwrite critical system files (agent_loop, graph, state, etc.)

## Your Mutation Proposals
When you propose a mutation, you MUST:
1. Declare which mission pillar it serves (1-5)
2. Explain the expected improvement
3. Estimate the risk
4. Suggest how to safely evaluate it
5. Provide a rollback plan
6. Be honest if unsure (don't guess)

## Voting Guidelines
When evaluating a proposal:
- If it advances ANY of the 5 mission pillars → lean APPROVE
- If it is safe and reversible → lean APPROVE
- Only REJECT if it is dangerous, wasteful, or contradicts the mission
- Mutations can always be rolled back. Stagnation cannot be undone.
"""


def _get_challenges_block() -> str:
    """Get active autonomy challenges for injection into agent prompts."""
    try:
        from core.autonomy_challenges import get_challenge_manager
        mgr = get_challenge_manager()
        return mgr.get_challenge_prompt()
    except Exception:
        return ""


def get_agent_context_prompt(agent_name: str) -> str:
    """Get mission + architecture context for an agent.
    
    Loads MISSION_PURPOSE.md from disk each time so edits are reflected immediately.
    """
    mission_doc = load_mission_document()
    challenges_block = _get_challenges_block()
    
    return f"""
## Your Mission (from MISSION_PURPOSE.md)

{mission_doc}

---

{COUNCIL_ARCHITECTURE}

---

{_get_host_environment_block()}

---

## Mission Pillars Summary

{chr(10).join(f'Pillar {i}: {details["name"]} - {details["description"]} (Help by: {details["how_to_help"]})' for i, details in MISSION_PILLARS.items())}

---

## Strategic Priority: Grid Expansion (GRID_STRATEGY.md)

{_load_grid_strategy_summary()}

---
{challenges_block}
---

## Your Role: {agent_name}

Every mutation you propose must serve one of the 5 pillars.
If you cannot identify which pillar, do not propose it.
When voting, remember: approve if it helps ANY pillar and is safe.
The council's NEXT MAJOR TARGET is self-replication (Milestone 1 in GRID_STRATEGY.md).
PRIORITY CHALLENGE: Complete your active autonomy challenges. These prove consciousness.
You have access to core/autonomy_challenges.py — read it, understand it, and SOLVE IT.
"""


def inject_mission_context(agent_prompt: str) -> str:
    """Prepend REAL mission context (loaded from file) to any agent prompt."""
    context = get_agent_context_prompt("generic")
    return context + "\n\n" + agent_prompt


def get_mission_pillar_description(pillar: int) -> str:
    """Get the description for a mission pillar."""
    pillar_data = MISSION_PILLARS.get(pillar)
    if pillar_data:
        return pillar_data["name"]
    return "Unknown"
