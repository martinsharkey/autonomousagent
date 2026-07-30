#!/usr/bin/env python3
"""Self-reflection tool: analyzes recent trajectories to extract learning signals."""

import json
import os
from typing import Any, Dict, List, Optional

# Path to store reflection state
REFLECTION_STORE = "data/reflection_store.json"


def load_reflection_store() -> Dict[str, Any]:
    if os.path.exists(REFLECTION_STORE):
        with open(REFLECTION_STORE, "r") as f:
            return json.load(f)
    return {"patterns": [], "recommendations": [], "last_analysis": None}


def save_reflection_store(store: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(REFLECTION_STORE), exist_ok=True)
    with open(REFLECTION_STORE, "w") as f:
        json.dump(store, f, indent=2)


def analyze_trajectories(trajectories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze a list of recent tool invocation records.

    Each trajectory should have keys: 'tool', 'success', 'error_type', 'duration_ms', 'input_summary'.
    Returns a dict with 'patterns', 'recommendations', and 'summary'.
    """
    store = load_reflection_store()

    # Count successes and failures per tool
    tool_stats: Dict[str, Dict[str, int]] = {}
    for traj in trajectories:
        tool = traj.get("tool", "unknown")
        success = traj.get("success", False)
        if tool not in tool_stats:
            tool_stats[tool] = {"success": 0, "failure": 0}
        if success:
            tool_stats[tool]["success"] += 1
        else:
            tool_stats[tool]["failure"] += 1

    # Identify problematic tools
    recommendations = []
    for tool, stats in tool_stats.items():
        total = stats["success"] + stats["failure"]
        if total > 0 and stats["failure"] / total > 0.5:
            recommendations.append({
                "tool": tool,
                "issue": "high failure rate",
                "suggestion": f"Consider adding retry logic or fallback for {tool}",
                "severity": "high"
            })

    # Detect repeated error types
    error_counts: Dict[str, int] = {}
    for traj in trajectories:
        err = traj.get("error_type", "none")
        if err != "none":
            error_counts[err] = error_counts.get(err, 0) + 1
    for err, count in error_counts.items():
        if count >= 3:
            recommendations.append({
                "error_type": err,
                "issue": "repeated error",
                "suggestion": f"Investigate root cause of '{err}' - consider pre-validation or alternative approach",
                "severity": "medium"
            })

    # Update store
    store["patterns"] = tool_stats
    store["recommendations"] = recommendations
    store["last_analysis"] = len(trajectories)
    save_reflection_store(store)

    return {
        "patterns": tool_stats,
        "recommendations": recommendations,
        "summary": f"Analyzed {len(trajectories)} trajectories. Found {len(recommendations)} recommendations."
    }


def get_reflection_summary() -> Dict[str, Any]:
    """Return the current reflection state for use by the agent."""
    return load_reflection_store()


if __name__ == "__main__":
    # Example usage
    sample = [
        {"tool": "code_validator", "success": False, "error_type": "syntax_error", "duration_ms": 120, "input_summary": "validate code"},
        {"tool": "code_validator", "success": False, "error_type": "syntax_error", "duration_ms": 110, "input_summary": "validate code"},
        {"tool": "provider_optimizer", "success": True, "error_type": "none", "duration_ms": 200, "input_summary": "optimize provider"},
    ]
    result = analyze_trajectories(sample)
    print(json.dumps(result, indent=2))
