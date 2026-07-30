import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class SelfReflection:
    """Tool to log, categorize, and learn from errors and failures."""

    def __init__(self, log_path: str = "reflection_log.json"):
        self.log_path = log_path
        self._ensure_log()

    def _ensure_log(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                json.dump([], f)

    def log_error(self, tool_name: str, error: str, context: Dict = None):
        """Log a failed tool invocation with metadata."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "error": str(error),
            "context": context or {},
            "category": self._categorize_error(error)
        }
        with open(self.log_path, "r") as f:
            logs = json.load(f)
        logs.append(entry)
        with open(self.log_path, "w") as f:
            json.dump(logs, f, indent=2)
        return entry

    def _categorize_error(self, error: str) -> str:
        error_lower = error.lower()
        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "permission" in error_lower or "denied" in error_lower:
            return "permission"
        elif "not found" in error_lower or "does not exist" in error_lower:
            return "missing_resource"
        elif "invalid" in error_lower or "syntax" in error_lower:
            return "invalid_input"
        elif "connection" in error_lower or "network" in error_lower:
            return "network"
        else:
            return "unknown"

    def get_error_summary(self) -> Dict:
        """Return aggregated error statistics."""
        with open(self.log_path, "r") as f:
            logs = json.load(f)
        if not logs:
            return {"total": 0, "categories": {}}
        categories = {}
        for entry in logs:
            cat = entry["category"]
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total": len(logs),
            "categories": categories,
            "most_common_tool": max(set(e["tool"] for e in logs), key=lambda t: sum(1 for e in logs if e["tool"] == t))
        }

    def suggest_improvements(self) -> List[str]:
        """Generate actionable suggestions based on error patterns."""
        summary = self.get_error_summary()
        suggestions = []
        if summary["total"] == 0:
            return ["No errors recorded. Continue monitoring."]
        cats = summary["categories"]
        if "timeout" in cats and cats["timeout"] > 2:
            suggestions.append("Increase timeout thresholds or implement retry with exponential backoff.")
        if "permission" in cats and cats["permission"] > 2:
            suggestions.append("Review access rights and API keys for required resources.")
        if "missing_resource" in cats and cats["missing_resource"] > 2:
            suggestions.append("Add pre-checks for resource existence before tool calls.")
        if "network" in cats and cats["network"] > 2:
            suggestions.append("Implement fallback providers or offline mode.")
        if "invalid_input" in cats and cats["invalid_input"] > 2:
            suggestions.append("Add input validation and sanitization before tool calls.")
        if not suggestions:
            suggestions.append("Review individual error logs for patterns.")
        return suggestions

    def clear_log(self):
        """Reset the error log."""
        with open(self.log_path, "w") as f:
            json.dump([], f)
