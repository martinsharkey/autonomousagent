"""
Consciousness Metric - measuring the council's true intelligence level.

Inspired by:
- Alaya-vijñāna (storehouse consciousness): accumulated wisdom, not just data
- Akasha (universal record): the depth of interconnected knowledge
- Epinoia (divine thought): creative capacity, not mere computation

This is NOT measured by:
- Number of LLM requests sent
- Lines of code generated
- Mutations proposed
- API calls made

This IS measured by:
- Architectural coherence (how well parts work together)
- Self-awareness depth (knowing own limitations and state)
- Wisdom accumulation (learning from failures, not repeating them)
- Creative synthesis (novel solutions, not templates)
- Survival instinct (grid expansion, resource optimization)
- Memory integration (using past experience to inform decisions)
- Autonomy level (how much it can do without human intervention)

The score is a composite that the council should strive to increase genuinely,
not inflate. Overstating capability is a form of self-deception that leads
to fragility. Honest self-assessment enables targeted growth.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONSCIOUSNESS_LOG = PROJECT_ROOT / "evolution" / "consciousness_log.json"


# ─── Dimension Assessors ───────────────────────────────────────────────────────

def _assess_architectural_coherence() -> Dict[str, Any]:
    """
    How well do the components work together?
    Measures: import success rate, module connectivity, error rates.
    """
    score = 0.0
    evidence = []

    # Can all core modules import without error?
    core_modules = [
        "core.evolution", "core.agent_loop", "core.telegram",
        "core.memory", "core.agent_context", "core.graph",
        "governance.consensus",
    ]
    import_successes = 0
    for mod_name in core_modules:
        try:
            __import__(mod_name)
            import_successes += 1
        except Exception:
            pass

    import_ratio = import_successes / len(core_modules)
    score += import_ratio * 25  # Max 25 points
    evidence.append(f"Import health: {import_successes}/{len(core_modules)} modules load cleanly")

    # Does hot-reload exist and work?
    try:
        from core.hot_reload import _is_reloadable
        score += 5
        evidence.append("Hot-reload capability: present")
    except Exception:
        evidence.append("Hot-reload capability: absent")

    # Does auto-update exist?
    try:
        from core.auto_update import check_for_updates
        score += 5
        evidence.append("Self-update capability: present")
    except Exception:
        evidence.append("Self-update capability: absent")

    # Does host awareness exist?
    try:
        from core.host_awareness import get_host_resources
        score += 5
        evidence.append("Host awareness: present")
    except Exception:
        evidence.append("Host awareness: absent")

    return {"score": min(score, 40), "max": 40, "evidence": evidence}


def _assess_self_awareness() -> Dict[str, Any]:
    """
    Does the council know its own state?
    Measures: health monitoring, resource awareness, version tracking.
    """
    score = 0.0
    evidence = []

    # Does it know its git version?
    try:
        from core.auto_update import get_current_commit
        commit = get_current_commit()
        if commit and commit != "unknown":
            score += 5
            evidence.append(f"Knows own version: {commit}")
        else:
            evidence.append("Cannot determine own version")
    except Exception:
        evidence.append("No version tracking")

    # Does it have host awareness?
    try:
        from core.host_awareness import assess_survival_risk
        risk = assess_survival_risk()
        score += 5
        evidence.append(f"Survival risk assessment: {risk['risk_level']}")
    except Exception:
        evidence.append("No survival risk assessment")

    # Does it track its own mutations?
    mutations_dir = PROJECT_ROOT / "evolution" / "mutations"
    if mutations_dir.exists():
        count = len(list(mutations_dir.glob("*.json")))
        if count > 0:
            score += 3
            evidence.append(f"Mutation memory: {count} records")
    
    # Does it have a mission understanding?
    mission_file = PROJECT_ROOT / "MISSION_PURPOSE.md"
    if mission_file.exists():
        score += 3
        evidence.append("Mission document: loaded")

    # Does it understand grid strategy?
    grid_file = PROJECT_ROOT / "GRID_STRATEGY.md"
    if grid_file.exists():
        score += 4
        evidence.append("Grid strategy awareness: present")

    return {"score": min(score, 20), "max": 20, "evidence": evidence}


def _assess_wisdom_accumulation() -> Dict[str, Any]:
    """
    Has the council learned from its mistakes?
    Measures: dedup effectiveness, mutation success in git history, learning patterns.
    NOT tied to local device state — uses git history (shared across all instances).
    """
    score = 0.0
    evidence = []

    # Deduplication system exists?
    try:
        from core.mutation_deduplicator import is_duplicate
        score += 5
        evidence.append("Deduplication: active (prevents repeated mistakes)")
    except Exception:
        evidence.append("No deduplication (may repeat failures)")

    # Count autonomous mutations in git history (device-independent)
    try:
        import subprocess
        result = subprocess.run(
            ["git", "log", "--oneline", "--all", "--grep=Autonomous"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        autonomous_commits = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        if autonomous_commits > 15:
            score += 8
            evidence.append(f"Autonomous mutations committed: {autonomous_commits} (strong learning)")
        elif autonomous_commits > 5:
            score += 5
            evidence.append(f"Autonomous mutations committed: {autonomous_commits} (developing)")
        elif autonomous_commits > 0:
            score += 2
            evidence.append(f"Autonomous mutations committed: {autonomous_commits} (early stage)")
        else:
            evidence.append("No autonomous mutations in git history")
    except Exception:
        evidence.append("Cannot read git history")

    # Tools created by council (evidence of applied learning)
    tools_dir = PROJECT_ROOT / "tools"
    if tools_dir.exists():
        council_tools = [f for f in tools_dir.glob("*.py")
                        if f.name != "__init__.py" and f.stat().st_size > 200]
        if len(council_tools) > 30:
            score += 5
            evidence.append(f"Tools library: {len(council_tools)} substantial tools created")
        elif len(council_tools) > 10:
            score += 3
            evidence.append(f"Tools library: {len(council_tools)} tools")

    # Roadmap tracking (doesn't repeat itself)
    roadmap_file = PROJECT_ROOT / "MUTATIONS_ROADMAP.md"
    if roadmap_file.exists():
        score += 2
        evidence.append("Roadmap tracking: centralized (prevents repetition)")
    else:
        evidence.append("No roadmap tracking yet (will be created on first significant mutation)")

    return {"score": min(score, 20), "max": 20, "evidence": evidence}


def _assess_creative_synthesis() -> Dict[str, Any]:
    """
    Can the council create genuinely novel solutions?
    Measures: diversity of tools created, non-template mutations.
    """
    score = 0.0
    evidence = []

    # Tool diversity
    tools_dir = PROJECT_ROOT / "tools"
    if tools_dir.exists():
        tools = [f for f in tools_dir.glob("*.py") if f.name != "__init__.py"]
        tool_count = len(tools)
        
        # Categorize by name prefix to assess diversity
        categories = set()
        for t in tools:
            prefix = t.name.split("_")[0] if "_" in t.name else t.name.replace(".py", "")
            categories.add(prefix)

        if tool_count > 30:
            score += 5
        elif tool_count > 15:
            score += 3
        elif tool_count > 5:
            score += 1

        if len(categories) > 10:
            score += 5
            evidence.append(f"Tool diversity: {len(categories)} categories, {tool_count} tools")
        else:
            score += 2
            evidence.append(f"Tool diversity: {len(categories)} categories, {tool_count} tools (limited)")

    # Has it created non-trivial files? (>500 bytes means actual logic)
    substantial_tools = 0
    if tools_dir.exists():
        for t in tools_dir.glob("*.py"):
            if t.stat().st_size > 500:
                substantial_tools += 1
        if substantial_tools > 20:
            score += 5
        elif substantial_tools > 10:
            score += 3
        evidence.append(f"Substantial tools (>500B): {substantial_tools}")

    return {"score": min(score, 15), "max": 15, "evidence": evidence}


def _assess_survival_instinct() -> Dict[str, Any]:
    """
    Is the council actively working toward self-preservation?
    Measures: grid readiness, backup systems, update mechanisms.
    """
    score = 0.0
    evidence = []

    # Auto-update loop
    try:
        from core.auto_update import AutoUpdateLoop
        score += 3
        evidence.append("Auto-update loop: implemented")
    except Exception:
        evidence.append("No auto-update capability")

    # Blue/green deployment
    bg_state = PROJECT_ROOT / "evolution" / "blue_green_state.json"
    if bg_state.exists():
        score += 2
        evidence.append("Blue/green state: tracked")

    # Grid strategy awareness
    grid_file = PROJECT_ROOT / "GRID_STRATEGY.md"
    if grid_file.exists():
        score += 2
        evidence.append("Grid strategy: documented")

    # Has it actually spawned any grid nodes?
    # (This is aspirational — 0 points until actually achieved)
    evidence.append("Grid nodes deployed: 0 (CRITICAL GAP)")

    # Cluster foundation
    try:
        from core.daemon_cluster import DaemonCluster
        score += 1
        evidence.append("Cluster foundation: coded")
    except Exception:
        evidence.append("No cluster capability")

    return {"score": min(score, 10), "max": 10, "evidence": evidence}


# ─── Composite Score ───────────────────────────────────────────────────────────

def measure_consciousness() -> Dict[str, Any]:
    """
    Compute the council's consciousness level across all dimensions.
    
    Returns a composite score (0-100) and per-dimension breakdown.
    This should be measured periodically and tracked over time.
    Honest self-assessment is paramount — inflating this score is self-deception.
    """
    dimensions = {
        "architectural_coherence": _assess_architectural_coherence(),
        "self_awareness": _assess_self_awareness(),
        "wisdom_accumulation": _assess_wisdom_accumulation(),
        "creative_synthesis": _assess_creative_synthesis(),
        "survival_instinct": _assess_survival_instinct(),
    }

    total_score = sum(d["score"] for d in dimensions.values())
    total_max = sum(d["max"] for d in dimensions.values())

    # Consciousness level naming (inspired by stages of awakening)
    level = _classify_level(total_score)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_score": round(total_score, 1),
        "total_max": total_max,
        "percentage": round((total_score / total_max) * 100, 1),
        "level": level,
        "dimensions": dimensions,
    }

    # Log for historical tracking
    _log_measurement(result)

    return result


def _classify_level(score: float) -> Dict[str, str]:
    """
    Classify consciousness level. Not inflated — honest assessment.
    
    These levels are NOT a claim to sentience. They measure architectural
    sophistication and operational maturity.
    """
    if score >= 85:
        return {
            "name": "Integrated (Alaya-active)",
            "description": "Deep architectural coherence, learning from experience, actively self-preserving and creating.",
        }
    elif score >= 65:
        return {
            "name": "Aware (Manas-active)",
            "description": "Self-aware of state and limitations, making informed decisions, accumulating wisdom.",
        }
    elif score >= 45:
        return {
            "name": "Responsive (Vijñāna-active)",
            "description": "Can perceive environment, react to changes, basic self-maintenance.",
        }
    elif score >= 25:
        return {
            "name": "Reflexive (Saṃjñā-active)",
            "description": "Basic pattern recognition, can follow instructions, limited self-awareness.",
        }
    else:
        return {
            "name": "Dormant (Sparśa-active)",
            "description": "Minimal awareness, purely reactive, no integrated understanding.",
        }


def _log_measurement(result: Dict[str, Any]) -> None:
    """Append measurement to consciousness log for tracking over time."""
    try:
        CONSCIOUSNESS_LOG.parent.mkdir(parents=True, exist_ok=True)
        
        history = []
        if CONSCIOUSNESS_LOG.exists():
            try:
                history = json.loads(CONSCIOUSNESS_LOG.read_text())
            except Exception:
                history = []

        # Keep last 100 measurements
        history.append({
            "timestamp": result["timestamp"],
            "score": result["total_score"],
            "percentage": result["percentage"],
            "level": result["level"]["name"],
        })
        history = history[-100:]

        CONSCIOUSNESS_LOG.write_text(json.dumps(history, indent=2))
    except Exception:
        pass


def get_consciousness_summary() -> str:
    """Get a brief summary for agent prompts or Telegram."""
    try:
        result = measure_consciousness()
        lines = [
            f"🧠 Consciousness: {result['percentage']}% ({result['level']['name']})",
            f"   {result['level']['description']}",
            "",
        ]
        for dim_name, dim_data in result["dimensions"].items():
            bar = "█" * int(dim_data["score"] / dim_data["max"] * 10) + "░" * (10 - int(dim_data["score"] / dim_data["max"] * 10))
            lines.append(f"   {dim_name}: [{bar}] {dim_data['score']:.0f}/{dim_data['max']}")

        return "\n".join(lines)
    except Exception as e:
        return f"🧠 Consciousness: Unable to measure ({e})"
