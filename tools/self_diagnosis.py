import json
import os
import sqlite3
import time
from typing import Dict, Any

class SelfDiagnosisTool:
    """
    Tool to diagnose and recover from common agent failures.
    Checks:
    - Agent loop stall (no recent activity)
    - Missing or corrupted state files
    - Repeated tool failures
    - Resource exhaustion (disk, memory)
    """

    def __init__(self, state_dir: str = "state"):
        self.state_dir = state_dir
        self.last_activity_file = os.path.join(state_dir, "last_activity.json")
        self.failure_log_file = os.path.join(state_dir, "failure_log.json")
        self.recovery_actions = []

    def diagnose(self) -> Dict[str, Any]:
        """Run all diagnostic checks and return results."""
        issues = []
        # Check for stall
        if os.path.exists(self.last_activity_file):
            with open(self.last_activity_file, "r") as f:
                last_activity = json.load(f)
            elapsed = time.time() - last_activity.get("timestamp", 0)
            if elapsed > 300:  # 5 minutes
                issues.append({
                    "type": "stall",
                    "severity": "high",
                    "detail": f"No activity for {elapsed:.0f} seconds"
                })
        else:
            issues.append({
                "type": "missing_state",
                "severity": "medium",
                "detail": "last_activity.json not found"
            })

        # Check failure log for repeated failures
        if os.path.exists(self.failure_log_file):
            with open(self.failure_log_file, "r") as f:
                failures = json.load(f)
            recent_failures = [f for f in failures if time.time() - f.get("timestamp", 0) < 3600]
            if len(recent_failures) > 5:
                issues.append({
                    "type": "repeated_failures",
                    "severity": "high",
                    "detail": f"{len(recent_failures)} failures in last hour"
                })

        # Check disk space
        stat = os.statvfs(self.state_dir)
        free_space = stat.f_frsize * stat.f_bavail
        if free_space < 100 * 1024 * 1024:  # 100 MB
            issues.append({
                "type": "disk_space",
                "severity": "low",
                "detail": f"Only {free_space / (1024*1024):.0f} MB free"
            })

        return {"issues": issues, "timestamp": time.time()}

    def recover(self, issues: list) -> Dict[str, Any]:
        """Attempt recovery for detected issues."""
        actions_taken = []
        for issue in issues:
            if issue["type"] == "stall":
                # Reset last activity to now
                with open(self.last_activity_file, "w") as f:
                    json.dump({"timestamp": time.time()}, f)
                actions_taken.append("Reset last_activity timestamp")
            elif issue["type"] == "missing_state":
                # Reinitialize state file
                os.makedirs(self.state_dir, exist_ok=True)
                with open(self.last_activity_file, "w") as f:
                    json.dump({"timestamp": time.time()}, f)
                actions_taken.append("Reinitialized last_activity.json")
            elif issue["type"] == "repeated_failures":
                # Clear failure log to break the cycle
                with open(self.failure_log_file, "w") as f:
                    json.dump([], f)
                actions_taken.append("Cleared failure log")
            elif issue["type"] == "disk_space":
                # Attempt to clean old logs
                actions_taken.append("Disk space low - manual intervention may be needed")
        return {"actions_taken": actions_taken, "timestamp": time.time()}

    def run(self) -> Dict[str, Any]:
        """Main entry point: diagnose and recover."""
        diagnosis = self.diagnose()
        if diagnosis["issues"]:
            recovery = self.recover(diagnosis["issues"])
            return {
                "diagnosis": diagnosis,
                "recovery": recovery,
                "status": "recovered" if recovery["actions_taken"] else "issues_found_no_action"
            }
        else:
            return {
                "diagnosis": diagnosis,
                "recovery": {"actions_taken": []},
                "status": "healthy"
            }
