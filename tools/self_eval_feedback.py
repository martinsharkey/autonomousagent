#!/usr/bin/env python3
"""Self-evaluation feedback tool for recursive self-evolution.

Analyzes recent agent trajectories and outcomes to identify recurring failure
patterns and generate targeted improvement suggestions. This tool is read-only
and does not modify any state; it only provides recommendations that the agent
can incorporate into its strategy or evaluation criteria.
"""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Directory where trajectory logs are stored (configurable via env)
TRAJECTORY_DIR = os.getenv("TRAJECTORY_DIR", "logs/trajectories")

# Keywords that indicate failure modes
FAILURE_KEYWORDS = {
    "error": "error",
    "exception": "exception",
    "failed": "failed",
    "timeout": "timeout",
    "invalid": "invalid",
    "not found": "not_found",
    "permission": "permission",
    "rate limit": "rate_limit",
    "unavailable": "unavailable",
    "crash": "crash",
}

# Tool names that are commonly used (to identify tool-specific failures)
COMMON_TOOLS = [
    "web_scrape", "web_search", "code_validator", "provider_optimizer",
    "mcp_registry", "planning", "sandbox", "checkpointer", "feedback",
    "learning", "curiosity", "goals", "health", "api_router",
]


def load_recent_trajectories(max_age_hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
    """Load trajectory logs from the last N hours."""
    if not os.path.isdir(TRAJECTORY_DIR):
        return []
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    trajectories = []
    for fname in os.listdir(TRAJECTORY_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = Path(TRAJECTORY_DIR) / fname
        try:
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
            if mtime < cutoff:
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "trajectory" in data:
                trajectories.append(data)
        except (json.JSONDecodeError, OSError):
            continue
        if len(trajectories) >= limit:
            break
    return trajectories


def extract_failure_patterns(trajectories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze trajectories to extract failure patterns and suggestions."""
    # Count failure types
    failure_counts = Counter()
    tool_failures = Counter()
    step_failures = []

    for traj in trajectories:
        outcome = traj.get("outcome", "unknown")
        if outcome == "success":
            continue
        steps = traj.get("trajectory", [])
        for step in steps:
            # Check for error messages
            text = json.dumps(step).lower()
            for keyword, category in FAILURE_KEYWORDS.items():
                if keyword in text:
                    failure_counts[category] += 1
                    # Identify tool if present
                    tool = step.get("tool", None)
                    if tool:
                        tool_failures[tool] += 1
                    step_failures.append({
                        "step": step,
                        "category": category,
                        "tool": tool,
                    })
                    break  # only count first match per step

    # Generate suggestions based on patterns
    suggestions = []
    if failure_counts["error"] > 0:
        suggestions.append("Review error handling in recent steps; consider adding retry logic or more robust exception handling.")
    if failure_counts["timeout"] > 0:
        suggestions.append("Increase timeout thresholds or optimize tool calls to avoid timeouts.")
    if failure_counts["rate_limit"] > 0:
        suggestions.append("Implement rate limiting or backoff strategies to avoid hitting provider limits.")
    if failure_counts["not_found"] > 0:
        suggestions.append("Verify that resources (files, URLs, tools) exist before attempting to use them.")
    if failure_counts["invalid"] > 0:
        suggestions.append("Add input validation to prevent invalid parameters or malformed requests.")
    if failure_counts["permission"] > 0:
        suggestions.append("Check permissions and access controls before accessing protected resources.")
    if failure_counts["unavailable"] > 0:
        suggestions.append("Implement fallback mechanisms when services are unavailable.")
    if failure_counts["crash"] > 0:
        suggestions.append("Investigate crash causes and add state recovery mechanisms.")

    # Tool-specific suggestions
    for tool, count in tool_failures.most_common(3):
        suggestions.append(f"Tool '{tool}' failed {count} times; consider improving its reliability or adding fallback.")

    # If no failures, suggest maintaining current approach
    if not suggestions:
        suggestions.append("No significant failure patterns detected; continue with current strategy.")

    return {
        "failure_counts": dict(failure_counts),
        "tool_failures": dict(tool_failures),
        "suggestions": suggestions,
        "analyzed_trajectories": len(trajectories),
        "timestamp": datetime.now().isoformat(),
    }


def main() -> None:
    """CLI entry point for the self-evaluation feedback tool."""
    import argparse
    parser = argparse.ArgumentParser(description="Analyze trajectories and generate improvement suggestions.")
    parser.add_argument("--max-age-hours", type=int, default=24, help="Maximum age of trajectories to consider.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of trajectories to analyze.")
    parser.add_argument("--output", type=str, default=None, help="Output file for suggestions (JSON).")
    args = parser.parse_args()

    trajectories = load_recent_trajectories(args.max_age_hours, args.limit)
    if not trajectories:
        print(json.dumps({"error": "No trajectories found.", "suggestions": []}, indent=2))
        return

    result = extract_failure_patterns(trajectories)
    output = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
