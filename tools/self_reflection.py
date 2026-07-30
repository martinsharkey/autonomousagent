"""Self-reflection tool: logs failures, extracts patterns, and suggests improvements."""
import json
import os
from datetime import datetime

REFLECTION_LOG = "session_log.md"

def log_failure(tool_name: str, error: str, context: dict) -> None:
    """Append a structured failure entry to the reflection log."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool_name,
        "error": error,
        "context": context
    }
    with open(REFLECTION_LOG, "a") as f:
        f.write(f"\n## Failure Log\n```json\n{json.dumps(entry, indent=2)}\n```\n")

def extract_patterns() -> list:
    """Parse the reflection log and return common error patterns."""
    if not os.path.exists(REFLECTION_LOG):
        return []
    with open(REFLECTION_LOG, "r") as f:
        content = f.read()
    # Simple pattern extraction: count error messages
    errors = [line for line in content.split("\n") if "error" in line.lower()]
    pattern_counts = {}
    for err in errors:
        pattern_counts[err] = pattern_counts.get(err, 0) + 1
    sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"pattern": p, "count": c} for p, c in sorted_patterns[:5]]

def suggest_improvements() -> list:
    """Generate actionable suggestions based on failure patterns."""
    patterns = extract_patterns()
    suggestions = []
    for p in patterns:
        if "timeout" in p["pattern"].lower():
            suggestions.append("Increase timeout or add retry logic for slow operations.")
        elif "permission" in p["pattern"].lower():
            suggestions.append("Check file permissions and ensure write access.")
        elif "not found" in p["pattern"].lower():
            suggestions.append("Verify file paths and existence before access.")
    return suggestions
