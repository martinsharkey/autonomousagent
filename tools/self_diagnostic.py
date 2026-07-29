"""Self-diagnostic and recovery tool for agent loop failures."""
import json
import os
import sqlite3
from datetime import datetime

DIAGNOSTIC_LOG = "diagnostic_log.json"

def run_diagnostics():
    """Run checks on agent state and return issues found."""
    issues = []
    # Check goal store integrity
    goal_db = "goals.db"
    if os.path.exists(goal_db):
        try:
            conn = sqlite3.connect(goal_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM goals")
            count = cursor.fetchone()[0]
            if count == 0:
                issues.append("Goal store is empty - no active goals")
            conn.close()
        except Exception as e:
            issues.append(f"Goal store corruption: {e}")
    else:
        issues.append("Goal store missing")
    # Check checkpoint integrity
    checkpoint_dir = "checkpoints"
    if os.path.isdir(checkpoint_dir):
        checkpoints = os.listdir(checkpoint_dir)
        if not checkpoints:
            issues.append("No checkpoints found")
        else:
            for cp in checkpoints:
                cp_path = os.path.join(checkpoint_dir, cp)
                if os.path.getsize(cp_path) == 0:
                    issues.append(f"Empty checkpoint: {cp}")
    else:
        issues.append("Checkpoint directory missing")
    # Check for stuck loops (e.g., repeated same error)
    log_file = "session_log.md"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()
        if "ERROR" in content:
            issues.append("Recent errors detected in session log")
    return issues

def recover_from_issue(issue):
    """Attempt recovery for a given issue."""
    if "Goal store" in issue:
        # Reinitialize goal store
        conn = sqlite3.connect("goals.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, description TEXT, status TEXT, created_at TEXT)")
        cursor.execute("INSERT INTO goals (description, status, created_at) VALUES ('Default recovery goal', 'active', ?)", (datetime.now().isoformat(),))
        conn.commit()
        conn.close()
        return "Reinitialized goal store with default goal"
    elif "Checkpoint" in issue:
        # Remove empty checkpoints
        checkpoint_dir = "checkpoints"
        if os.path.isdir(checkpoint_dir):
            for cp in os.listdir(checkpoint_dir):
                cp_path = os.path.join(checkpoint_dir, cp)
                if os.path.getsize(cp_path) == 0:
                    os.remove(cp_path)
        return "Cleaned empty checkpoints"
    elif "session log" in issue:
        # Archive old log and start fresh
        if os.path.exists("session_log.md"):
            os.rename("session_log.md", f"session_log_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        return "Archived session log"
    return "No recovery action available"

def main():
    """Main diagnostic entry point."""
    issues = run_diagnostics()
    result = {"timestamp": datetime.now().isoformat(), "issues": issues, "recoveries": []}
    for issue in issues:
        recovery = recover_from_issue(issue)
        result["recoveries"].append({"issue": issue, "action": recovery})
    # Log diagnostics
    with open(DIAGNOSTIC_LOG, "a") as f:
        f.write(json.dumps(result) + "\n")
    return result

if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
