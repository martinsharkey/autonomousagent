#!/usr/bin/env python3
"""State integrity verification and repair tool for durable local state."""
import sqlite3
import os
import json
import hashlib
from pathlib import Path

STATE_DIR = Path("state")
GOALS_DB = STATE_DIR / "goals.db"
CONFIG_FILE = STATE_DIR / "agent_config.json"
AUDIT_LOG = STATE_DIR / "audit.log"
CHECKPOINT_DIR = STATE_DIR / "checkpoints"

def verify_goals_db() -> list:
    issues = []
    if not GOALS_DB.exists():
        issues.append("goals.db missing")
        return issues
    try:
        conn = sqlite3.connect(str(GOALS_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM goals")
        count = cursor.fetchone()[0]
        if count < 0:
            issues.append("goals.db has negative count")
        conn.close()
    except Exception as e:
        issues.append(f"goals.db corruption: {e}")
    return issues

def verify_config() -> list:
    issues = []
    if not CONFIG_FILE.exists():
        issues.append("agent_config.json missing")
        return issues
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        if "version" not in data:
            issues.append("agent_config.json missing version")
    except Exception as e:
        issues.append(f"agent_config.json corruption: {e}")
    return issues

def verify_audit_log() -> list:
    issues = []
    if not AUDIT_LOG.exists():
        issues.append("audit.log missing")
        return issues
    try:
        with open(AUDIT_LOG, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            parts = line.strip().split("|")
            if len(parts) < 3:
                issues.append(f"audit.log line {i+1} malformed")
    except Exception as e:
        issues.append(f"audit.log corruption: {e}")
    return issues

def restore_from_checkpoint() -> bool:
    if not CHECKPOINT_DIR.exists():
        return False
    checkpoints = sorted(CHECKPOINT_DIR.glob("*.tar.gz"), reverse=True)
    if not checkpoints:
        return False
    latest = checkpoints[0]
    # Simulated restore: in production, extract and overwrite state files
    print(f"Restoring from checkpoint: {latest.name}")
    return True

def repair_state() -> list:
    issues = []
    issues.extend(verify_goals_db())
    issues.extend(verify_config())
    issues.extend(verify_audit_log())
    if issues:
        print("State issues detected:", issues)
        if restore_from_checkpoint():
            print("Restored from checkpoint. Re-verifying...")
            issues = []
            issues.extend(verify_goals_db())
            issues.extend(verify_config())
            issues.extend(verify_audit_log())
            if issues:
                print("Post-restore issues remain:", issues)
            else:
                print("All state files verified clean after restore.")
        else:
            print("No checkpoint available. Manual intervention required.")
    else:
        print("All state files verified clean.")
    return issues

if __name__ == "__main__":
    repair_state()
