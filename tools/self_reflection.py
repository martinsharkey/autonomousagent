import json
import traceback
from typing import Dict, Any, Optional

class SelfReflectionTool:
    """Analyzes recent failures and suggests improvements."""

    def __init__(self, log_path: str = "session_log.md"):
        self.log_path = log_path

    def analyze_failure(self, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Given error context (e.g., exception type, traceback, tool used),
        return a structured analysis with root cause and corrective actions.
        """
        analysis = {
            "error_type": error_context.get("error_type", "Unknown"),
            "tool_used": error_context.get("tool_used", "None"),
            "traceback_summary": self._summarize_traceback(error_context.get("traceback", "")),
            "root_cause": self._infer_root_cause(error_context),
            "corrective_actions": self._suggest_actions(error_context),
            "severity": self._assess_severity(error_context)
        }
        return analysis

    def _summarize_traceback(self, tb: str) -> str:
        lines = tb.strip().split('\n')
        # Keep last 5 lines for brevity
        return '\n'.join(lines[-5:])

    def _infer_root_cause(self, ctx: Dict[str, Any]) -> str:
        error_type = ctx.get("error_type", "")
        if "KeyError" in error_type:
            return "Missing expected key in data structure"
        elif "Timeout" in error_type:
            return "External service or tool took too long to respond"
        elif "Permission" in error_type:
            return "Insufficient permissions or resource not accessible"
        elif "ValueError" in error_type:
            return "Invalid input or malformed data"
        else:
            return "Unrecognized error pattern - manual review recommended"

    def _suggest_actions(self, ctx: Dict[str, Any]) -> list:
        error_type = ctx.get("error_type", "")
        suggestions = []
        if "KeyError" in error_type:
            suggestions.append("Add defensive checks for missing keys before access")
            suggestions.append("Use .get() with default values")
        elif "Timeout" in error_type:
            suggestions.append("Increase timeout or implement retry logic")
            suggestions.append("Consider fallback to alternative tool or provider")
        elif "Permission" in error_type:
            suggestions.append("Verify credentials and resource paths")
            suggestions.append("Check if resource exists and is accessible")
        else:
            suggestions.append("Log full context and escalate to human companion")
        return suggestions

    def _assess_severity(self, ctx: Dict[str, Any]) -> str:
        # Simple heuristic: if multiple failures in short time, high severity
        return "medium"

    def record_failure(self, error_context: Dict[str, Any]) -> None:
        """Append failure analysis to session log for future learning."""
        analysis = self.analyze_failure(error_context)
        with open(self.log_path, "a") as f:
            f.write("\n## Failure Analysis\n")
            f.write(f"- Error Type: {analysis['error_type']}\n")
            f.write(f"- Tool Used: {analysis['tool_used']}\n")
            f.write(f"- Root Cause: {analysis['root_cause']}\n")
            f.write(f"- Suggested Actions: {', '.join(analysis['corrective_actions'])}\n")
            f.write(f"- Severity: {analysis['severity']}\n")

# Singleton instance
_reflection_tool = None

def get_reflection_tool() -> SelfReflectionTool:
    global _reflection_tool
    if _reflection_tool is None:
        _reflection_tool = SelfReflectionTool()
    return _reflection_tool
