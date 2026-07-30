#!/usr/bin/env python3
"""Self-diagnostic and recovery tool for the autobot agent.

Scans and repairs common failure patterns in runtime state:
- Stale or orphaned goals in SQLite
- Corrupted or missing config entries
- Inconsistent audit log entries
- Stuck or looping agent states

Usage: invoked by the agent loop when success_rate drops below threshold.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Paths (configurable via env or defaults)
GOALS_DB_PATH = os.getenv("GOALS_DB_PATH", "data/goals.db")
CONFIG_DB_PATH = os.getenv("CONFIG_DB_PATH", "data/agent_config.db")
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "data/audit.log")


def diagnose_goals() -> Tuple[List[str], List[str]]:
    """Check goals database for stale or orphaned entries.
    Returns (issues_found, repairs_made).
    """
    issues = []
    repairs = []
    try:
        conn = sqlite3.connect(GOALS_DB_PATH)
        cursor = conn.cursor()
        # Check for goals older than 7 days with status 'active'
        cursor.execute("SELECT id, description, created_at FROM goals WHERE status='active' AND created_at < ?",
                       (datetime.now() - timedelta(days=7),))
        stale = cursor.fetchall()
        for goal_id, desc, created in stale:
            issues.append(f"Stale goal {goal_id}: '{desc}' created {created}")
            # Mark as 'archived'
            cursor.execute("UPDATE goals SET status='archived' WHERE id=?", (goal_id,))
            repairs.append(f"Archived stale goal {goal_id}")
        conn.commit()
        conn.close()
    except Exception as e:
        issues.append(f"Goals DB error: {e}")
    return issues, repairs


def diagnose_config() -> Tuple[List[str], List[str]]:
    """Check config database for missing or corrupted entries.
    Returns (issues_found, repairs_made).
    """
    issues = []
    repairs = []
    required_keys = ["max_retries", "system_prompt", "model_provider"]
    try:
        conn = sqlite3.connect(CONFIG_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM config")
        rows = cursor.fetchall()
        config_dict = {row[0]: row[1] for row in rows}
        for key in required_keys:
            if key not in config_dict:
                issues.append(f"Missing config key: {key}")
                # Insert default value
                default = {"max_retries": "3", "system_prompt": "You are a helpful assistant.", "model_provider": "openai"}.get(key, "")
                cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, default))
                repairs.append(f"Restored default config key {key}")
        # Check for malformed JSON values
        for key, value in rows:
            if key == "system_prompt":
                continue  # string, not JSON
            try:
                json.loads(value)
            except (json.JSONDecodeError, TypeError):
                issues.append(f"Corrupted config value for {key}: {value}")
                cursor.execute("DELETE FROM config WHERE key=?", (key,))
                repairs.append(f"Removed corrupted config key {key}")
        conn.commit()
        conn.close()
    except Exception as e:
        issues.append(f"Config DB error: {e}")
    return issues, repairs


def diagnose_audit_log() -> Tuple[List[str], List[str]]:
    """Check audit log for missing or truncated entries.
    Returns (issues_found, repairs_made).
    """
    issues = []
    repairs = []
    if not os.path.exists(AUDIT_LOG_PATH):
        issues.append("Audit log file missing")
        # Create empty log
        with open(AUDIT_LOG_PATH, "w") as f:
            f.write("# Audit log initialized by self-diagnostic\n")
        repairs.append("Created empty audit log")
        return issues, repairs
    try:
        with open(AUDIT_LOG_PATH, "r") as f:
            lines = f.readlines()
        if len(lines) < 2:
            issues.append("Audit log has fewer than 2 lines, may be truncated")
            # Append a marker
            with open(AUDIT_LOG_PATH, "a") as f:
                f.write(f"# Diagnostic repair at {datetime.now().isoformat()}\n")
            repairs.append("Added diagnostic marker to audit log")
    except Exception as e:
        issues.append(f"Audit log read error: {e}")
    return issues, repairs


def run_full_diagnostic() -> Dict[str, object]:
    """Run all diagnostic checks and return summary."""
    all_issues = []
    all_repairs = []
    
    issues, repairs = diagnose_goals()
    all_issues.extend(issues)
    all_repairs.extend(repairs)
    
    issues, repairs = diagnose_config()
    all_issues.extend(issues)
    all_repairs.extend(repairs)
    
    issues, repairs = diagnose_audit_log()
    all_issues.extend(issues)
    all_repairs.extend(repairs)
    
    return {
        "issues_found": all_issues,
        "repairs_made": all_repairs,
        "healthy": len(all_issues) == 0
    }


if __name__ == "__main__":
    result = run_full_diagnostic()
    print(json.dumps(result, indent=2))
