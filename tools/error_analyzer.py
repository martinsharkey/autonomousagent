#!/usr/bin/env python3
"""Error analysis and self-diagnostic tool for recursive self-evolution."""

import json
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

ERROR_LOG_PATH = "error_analysis_log.json"
MAX_LOG_ENTRIES = 100


def log_error(
    tool_name: str,
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a tool invocation error with context."""
    entry = {
        "timestamp": time.time(),
        "tool_name": tool_name,
        "error_type": error_type,
        "error_message": error_message,
        "context": context or {},
    }
    logs = _load_logs()
    logs.append(entry)
    if len(logs) > MAX_LOG_ENTRIES:
        logs = logs[-MAX_LOG_ENTRIES:]
    _save_logs(logs)


def analyze_errors() -> Dict[str, Any]:
    """Analyze logged errors and produce recommendations."""
    logs = _load_logs()
    if not logs:
        return {"status": "no_errors", "recommendations": []}

    # Group by tool and error type
    tool_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for entry in logs:
        tool = entry["tool_name"]
        etype = entry["error_type"]
        tool_stats[tool][etype] += 1

    recommendations = []
    for tool, error_counts in tool_stats.items():
        total = sum(error_counts.values())
        if total >= 3:
            top_error = max(error_counts, key=error_counts.get)
            recommendations.append({
                "tool": tool,
                "total_errors": total,
                "top_error_type": top_error,
                "suggestion": f"Consider reviewing {tool} for recurring {top_error} errors. Add retry logic or input validation.",
            })

    return {
        "status": "analyzed",
        "total_errors": len(logs),
        "unique_tools": len(tool_stats),
        "recommendations": recommendations,
    }


def clear_logs() -> None:
    """Clear the error log."""
    if os.path.exists(ERROR_LOG_PATH):
        os.remove(ERROR_LOG_PATH)


def _load_logs() -> List[Dict[str, Any]]:
    if not os.path.exists(ERROR_LOG_PATH):
        return []
    try:
        with open(ERROR_LOG_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_logs(logs: List[Dict[str, Any]]) -> None:
    with open(ERROR_LOG_PATH, "w") as f:
        json.dump(logs, f, indent=2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        result = analyze_errors()
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python error_analyzer.py analyze")
