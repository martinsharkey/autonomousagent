import json
import os
from collections import defaultdict
from datetime import datetime

ERROR_LOG_PATH = "error_analysis_log.json"

class ErrorAnalyzer:
    def __init__(self):
        self.error_log = self._load_log()

    def _load_log(self):
        if os.path.exists(ERROR_LOG_PATH):
            with open(ERROR_LOG_PATH, "r") as f:
                return json.load(f)
        return {"errors": [], "patterns": {}}

    def _save_log(self):
        with open(ERROR_LOG_PATH, "w") as f:
            json.dump(self.error_log, f, indent=2)

    def record_error(self, tool_name: str, error_type: str, error_message: str, context: dict = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        self.error_log["errors"].append(entry)
        self._update_patterns(tool_name, error_type)
        self._save_log()
        return {"status": "recorded", "entry": entry}

    def _update_patterns(self, tool_name: str, error_type: str):
        key = f"{tool_name}:{error_type}"
        if key not in self.error_log["patterns"]:
            self.error_log["patterns"][key] = {"count": 0, "last_seen": None}
        self.error_log["patterns"][key]["count"] += 1
        self.error_log["patterns"][key]["last_seen"] = datetime.utcnow().isoformat()

    def analyze_patterns(self, min_count: int = 2):
        suggestions = []
        for key, data in self.error_log["patterns"].items():
            if data["count"] >= min_count:
                tool, error_type = key.split(":", 1)
                suggestions.append({
                    "tool": tool,
                    "error_type": error_type,
                    "frequency": data["count"],
                    "suggestion": f"Consider adding retry logic or input validation for {tool} when encountering {error_type}."
                })
        return {"patterns": suggestions, "total_errors": len(self.error_log["errors"])}

    def get_recent_errors(self, limit: int = 10):
        recent = self.error_log["errors"][-limit:]
        return {"recent_errors": recent}

    def clear_log(self):
        self.error_log = {"errors": [], "patterns": {}}
        self._save_log()
        return {"status": "cleared"}

# Tool interface for MCP registry
def error_analyzer_tool(action: str, **kwargs):
    analyzer = ErrorAnalyzer()
    if action == "record":
        return analyzer.record_error(kwargs.get("tool_name"), kwargs.get("error_type"), kwargs.get("error_message"), kwargs.get("context"))
    elif action == "analyze":
        return analyzer.analyze_patterns(kwargs.get("min_count", 2))
    elif action == "recent":
        return analyzer.get_recent_errors(kwargs.get("limit", 10))
    elif action == "clear":
        return analyzer.clear_log()
    else:
        return {"error": f"Unknown action: {action}"}
