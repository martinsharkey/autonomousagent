import json
import sqlite3
from datetime import datetime
from pathlib import Path

def get_goals(db_path: str = "data/goals.db") -> list:
    """Fetch pending and recent goals from SQLite goal store."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, description, status, created_at, updated_at FROM goals ORDER BY updated_at DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "description": r[1], "status": r[2], "created_at": r[3], "updated_at": r[4]} for r in rows]
    except Exception as e:
        return [{"error": str(e)}]

def get_recent_logs(log_path: str = "session_log.md", lines: int = 20) -> str:
    """Read last N lines from session log."""
    try:
        p = Path(log_path)
        if not p.exists():
            return "No session log found."
        with open(p, "r") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:])
    except Exception as e:
        return f"Error reading log: {e}"

def generate_status_report() -> str:
    """Generate a human-readable status report."""
    now = datetime.utcnow().isoformat()
    goals = get_goals()
    recent = get_recent_logs()
    pending = [g for g in goals if g.get("status") in ("pending", "in_progress")]
    completed = [g for g in goals if g.get("status") == "completed"]
    report = f"*Autobot Status Report* ({now})\n\n"
    report += f"*Pending Goals:* {len(pending)}\n"
    for g in pending[:5]:
        report += f"- {g['description']} (status: {g['status']})\n"
    report += f"\n*Completed Goals (last 10):* {len(completed)}\n"
    for g in completed[:3]:
        report += f"- {g['description']}\n"
    report += f"\n*Recent Session Log (last {20} lines):*\n```\n{recent}\n```\n"
    return report

if __name__ == "__main__":
    print(generate_status_report())
