import json
import os
from collections import Counter
from datetime import datetime

ERROR_LOG_PATH = "error_log.json"
MAX_LOG_SIZE = 100

class ErrorAnalyzer:
    """Logs and analyzes tool invocation failures to suggest corrective actions."""

    def __init__(self):
        self.errors = self._load_errors()

    def _load_errors(self):
        if os.path.exists(ERROR_LOG_PATH):
            with open(ERROR_LOG_PATH, "r") as f:
                return json.load(f)
        return []

    def _save_errors(self):
        with open(ERROR_LOG_PATH, "w") as f:
            json.dump(self.errors[-MAX_LOG_SIZE:], f, indent=2)

    def log_error(self, tool_name: str, error_type: str, error_message: str, context: dict = None):
        """Record a tool invocation failure."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        self.errors.append(entry)
        self._save_errors()

    def analyze_patterns(self):
        """Return common error patterns and suggested fixes."""
        if not self.errors:
            return {"patterns": [], "suggestions": []}

        tool_counts = Counter(e["tool"] for e in self.errors)
        error_type_counts = Counter(e["error_type"] for e in self.errors)

        patterns = []
        suggestions = []

        # Most failing tool
        if tool_counts:
            worst_tool = tool_counts.most_common(1)[0]
            patterns.append(f"Tool '{worst_tool[0]}' failed {worst_tool[1]} times.")
            suggestions.append(f"Consider reviewing or replacing '{worst_tool[0]}'.")

        # Most common error type
        if error_type_counts:
            worst_error = error_type_counts.most_common(1)[0]
            patterns.append(f"Error type '{worst_error[0]}' occurred {worst_error[1]} times.")
            if worst_error[0] == "TimeoutError":
                suggestions.append("Increase timeout or add retry logic.")
            elif worst_error[0] == "ValueError":
                suggestions.append("Validate inputs before calling the tool.")
            elif worst_error[0] == "ConnectionError":
                suggestions.append("Check network connectivity or provider status.")

        return {
            "patterns": patterns,
            "suggestions": suggestions,
            "total_errors": len(self.errors)
        }

    def clear_log(self):
        """Reset the error log."""
        self.errors = []
        self._save_errors()

# Singleton for easy import
analyzer = ErrorAnalyzer()

def log_tool_error(tool_name: str, error_type: str, error_message: str, context: dict = None):
    analyzer.log_error(tool_name, error_type, error_message, context)

def get_error_analysis():
    return analyzer.analyze_patterns()
