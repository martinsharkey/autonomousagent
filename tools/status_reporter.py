import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

def generate_status_report() -> str:
    """Generate a human-readable status report for the agent."""
    report_parts = []
    
    # Load goals from SQLite
    goals_db = Path("data/goals.db")
    if goals_db.exists():
        conn = sqlite3.connect(str(goals_db))
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, description, status, created_at, updated_at FROM goals ORDER BY updated_at DESC LIMIT 5")
            goals = cursor.fetchall()
            if goals:
                report_parts.append("**Recent Goals:**")
                for g in goals:
                    report_parts.append(f"- Goal #{g[0]}: {g[1][:60]}... Status: {g[2]}, Updated: {g[4]}")
            else:
                report_parts.append("No recent goals.")
        finally:
            conn.close()
    else:
        report_parts.append("No goals database found.")
    
    # Load recent session log entries
    session_log = Path("session_log.md")
    if session_log.exists():
        with open(session_log, "r") as f:
            lines = f.readlines()
        recent = [l.strip() for l in lines[-10:] if l.strip()]
        if recent:
            report_parts.append("\n**Recent Activity:**")
            for line in recent:
                report_parts.append(f"- {line[:100]}")
        else:
            report_parts.append("\nNo recent activity logged.")
    else:
        report_parts.append("\nNo session log found.")
    
    # Check health status
    try:
        from core.health import check_health
        health = check_health()
        report_parts.append(f"\n**Health Status:** {health.get('status', 'unknown')}")
    except ImportError:
        report_parts.append("\nHealth check not available.")
    
    # Add timestamp
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    report_parts.append(f"\n_Report generated at {now}_")
    
    return "\n".join(report_parts)

if __name__ == "__main__":
    print(generate_status_report())
