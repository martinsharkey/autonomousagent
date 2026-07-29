import json
import os
from datetime import datetime
from collections import Counter

ERROR_LOG_PATH = "session_log.md"
DIAGNOSTIC_DB = "diagnostic_store.json"

class SelfDiagnostic:
    def __init__(self):
        self.error_history = self._load_history()

    def _load_history(self):
        if os.path.exists(DIAGNOSTIC_DB):
            with open(DIAGNOSTIC_DB, "r") as f:
                return json.load(f)
        return {"errors": [], "patterns": {}, "suggestions": []}

    def _save_history(self):
        with open(DIAGNOSTIC_DB, "w") as f:
            json.dump(self.error_history, f, indent=2)

    def log_error(self, tool_name: str, error_msg: str, context: dict = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "error": error_msg,
            "context": context or {}
        }
        self.error_history["errors"].append(entry)
        self._update_patterns(tool_name, error_msg)
        self._generate_suggestions()
        self._save_history()
        return {"logged": True, "entry_id": len(self.error_history["errors"]) - 1}

    def _update_patterns(self, tool_name: str, error_msg: str):
        key = f"{tool_name}::{error_msg[:50]}"
        if key not in self.error_history["patterns"]:
            self.error_history["patterns"][key] = {"count": 0, "first_seen": datetime.utcnow().isoformat()}
        self.error_history["patterns"][key]["count"] += 1
        self.error_history["patterns"][key]["last_seen"] = datetime.utcnow().isoformat()

    def _generate_suggestions(self):
        # Simple heuristic: if same error occurs >3 times, suggest a fix
        suggestions = []
        for key, pattern in self.error_history["patterns"].items():
            if pattern["count"] >= 3:
                tool = key.split("::")[0]
                suggestions.append({
                    "pattern": key,
                    "count": pattern["count"],
                    "suggestion": f"Recurring error in {tool}. Consider reviewing input validation or retry logic.",
                    "severity": "high" if pattern["count"] > 5 else "medium"
                })
        self.error_history["suggestions"] = suggestions[-10:]  # keep last 10

    def get_diagnostics(self):
        return {
            "total_errors": len(self.error_history["errors"]),
            "unique_patterns": len(self.error_history["patterns"]),
            "active_suggestions": self.error_history["suggestions"],
            "recent_errors": self.error_history["errors"][-5:]
        }

    def clear_history(self):
        self.error_history = {"errors": [], "patterns": {}, "suggestions": []}
        self._save_history()
        return {"cleared": True}

if __name__ == "__main__":
    diag = SelfDiagnostic()
    print(json.dumps(diag.get_diagnostics(), indent=2))
