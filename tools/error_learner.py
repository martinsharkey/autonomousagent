import json
import os
from datetime import datetime
from collections import defaultdict

ERROR_LOG_PATH = "error_learner_log.json"

class ErrorLearner:
    def __init__(self):
        self.log = self._load_log()

    def _load_log(self):
        if os.path.exists(ERROR_LOG_PATH):
            with open(ERROR_LOG_PATH, "r") as f:
                return json.load(f)
        return {"errors": [], "patterns": {}}

    def _save_log(self):
        with open(ERROR_LOG_PATH, "w") as f:
            json.dump(self.log, f, indent=2)

    def record_error(self, tool_name, error_type, error_message, context):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "error_type": error_type,
            "error_message": error_message,
            "context": context
        }
        self.log["errors"].append(entry)
        self._update_patterns(tool_name, error_type)
        self._save_log()
        return {"status": "recorded", "entry": entry}

    def _update_patterns(self, tool_name, error_type):
        key = f"{tool_name}:{error_type}"
        if key not in self.log["patterns"]:
            self.log["patterns"][key] = {"count": 0, "suggestions": []}
        self.log["patterns"][key]["count"] += 1
        # Generate suggestion based on error type
        suggestion = self._generate_suggestion(tool_name, error_type)
        if suggestion:
            self.log["patterns"][key]["suggestions"].append(suggestion)

    def _generate_suggestion(self, tool_name, error_type):
        suggestions_map = {
            "timeout": f"Consider increasing timeout or retry logic for {tool_name}",
            "connection": f"Check network connectivity or API endpoint for {tool_name}",
            "permission": f"Verify access rights or credentials for {tool_name}",
            "parsing": f"Review input format or response structure for {tool_name}",
            "missing_dependency": f"Install required library or module for {tool_name}",
        }
        return suggestions_map.get(error_type, f"Review {tool_name} implementation for {error_type}")

    def get_analysis(self):
        if not self.log["errors"]:
            return {"status": "no_errors", "summary": "No errors recorded yet."}
        total = len(self.log["errors"])
        top_patterns = sorted(self.log["patterns"].items(), key=lambda x: x[1]["count"], reverse=True)[:5]
        summary = {
            "total_errors": total,
            "top_patterns": [
                {"pattern": p, "count": d["count"], "suggestion": d["suggestions"][-1] if d["suggestions"] else ""}
                for p, d in top_patterns
            ]
        }
        return summary

    def suggest_fixes(self):
        analysis = self.get_analysis()
        if analysis.get("status") == "no_errors":
            return []
        fixes = []
        for pattern in analysis.get("top_patterns", []):
            fixes.append({
                "pattern": pattern["pattern"],
                "count": pattern["count"],
                "suggestion": pattern["suggestion"]
            })
        return fixes

# Singleton instance
error_learner = ErrorLearner()

def record_error(tool_name, error_type, error_message, context=""):
    return error_learner.record_error(tool_name, error_type, error_message, context)

def get_error_analysis():
    return error_learner.get_analysis()

def suggest_fixes():
    return error_learner.suggest_fixes()
