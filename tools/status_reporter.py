import json
import sqlite3
from datetime import datetime
from pathlib import Path

def get_goal_summary(db_path: str = "goals.db") -> str:
    """Return a plain-text summary of current goals."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, description, status, created_at FROM goals ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No goals recorded."
        lines = ["Current goals:"]
        for row in rows:
            lines.append(f"- Goal #{row[0]}: {row[1][:60]}... Status: {row[2]} (created {row[3]})")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not retrieve goals: {e}"

def get_recent_actions(log_path: str = "session_log.md", max_lines: int = 10) -> str:
    """Return the most recent actions from the session log."""
    try:
        p = Path(log_path)
        if not p.exists():
            return "No session log found."
        lines = p.read_text().splitlines()
        recent = lines[-max_lines:] if len(lines) > max_lines else lines
        return "Recent actions:\n" + "\n".join(recent)
    except Exception as e:
        return f"Could not read session log: {e}"

def get_health_summary() -> str:
    """Return a simple health status string."""
    try:
        from core.health import check_health
        result = check_health()
        return f"Health check: {result.get('status', 'unknown')}"
    except Exception:
        return "Health check unavailable."

def generate_status_report(include_goals: bool = True, include_actions: bool = True, include_health: bool = True) -> str:
    """Generate a human-readable status report."""
    parts = []
    parts.append(f"Status report generated at {datetime.utcnow().isoformat()}Z")
    if include_goals:
        parts.append(get_goal_summary())
    if include_actions:
        parts.append(get_recent_actions())
    if include_health:
        parts.append(get_health_summary())
    return "\n\n".join(parts)

if __name__ == "__main__":
    print(generate_status_report())
