#!/usr/bin/env python3
"""State integrity verification and repair tool for durable local state."""
import sqlite3
import json
import os
import hashlib
from pathlib import Path

# Paths to state files (relative to project root)
STATE_DIR = Path("state")
CHECKPOINT_DIR = STATE_DIR / "checkpoints"
GOALS_DB = STATE_DIR / "goals.db"
CONFIG_DB = STATE_DIR / "agent_config.db"

# Expected schema versions
EXPECTED_GOALS_SCHEMA = 1
EXPECTED_CONFIG_SCHEMA = 1

def verify_goals_db():
    """Check goals.db integrity and schema version."""
    if not GOALS_DB.exists():
        return {"status": "missing", "action": "create"}
    try:
        conn = sqlite3.connect(str(GOALS_DB))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            conn.close()
            return {"status": "corrupt", "detail": integrity}
        cursor.execute("PRAGMA schema_version")
        version = cursor.fetchone()[0]
        conn.close()
        if version != EXPECTED_GOALS_SCHEMA:
            return {"status": "schema_mismatch", "expected": EXPECTED_GOALS_SCHEMA, "actual": version}
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def verify_config_db():
    """Check agent_config.db integrity and schema version."""
    if not CONFIG_DB.exists():
        return {"status": "missing", "action": "create"}
    try:
        conn = sqlite3.connect(str(CONFIG_DB))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            conn.close()
            return {"status": "corrupt", "detail": integrity}
        cursor.execute("PRAGMA schema_version")
        version = cursor.fetchone()[0]
        conn.close()
        if version != EXPECTED_CONFIG_SCHEMA:
            return {"status": "schema_mismatch", "expected": EXPECTED_CONFIG_SCHEMA, "actual": version}
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def verify_checkpoints():
    """Check checkpoint files for integrity (hash verification)."""
    if not CHECKPOINT_DIR.exists():
        return {"status": "missing", "action": "create"}
    results = []
    for f in CHECKPOINT_DIR.glob("*.json"):
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
            # Check for required fields
            if "state" not in data or "timestamp" not in data:
                results.append({"file": f.name, "status": "invalid_format"})
                continue
            # Optional: verify checksum if present
            if "checksum" in data:
                computed = hashlib.sha256(json.dumps(data["state"], sort_keys=True).encode()).hexdigest()
                if computed != data["checksum"]:
                    results.append({"file": f.name, "status": "checksum_mismatch"})
                    continue
            results.append({"file": f.name, "status": "ok"})
        except Exception as e:
            results.append({"file": f.name, "status": "error", "detail": str(e)})
    return results

def repair_goals_db():
    """Attempt to repair or recreate goals.db."""
    try:
        if GOALS_DB.exists():
            os.remove(str(GOALS_DB))
        conn = sqlite3.connect(str(GOALS_DB))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, description TEXT, status TEXT, created_at TEXT, updated_at TEXT)")
        cursor.execute("PRAGMA schema_version = ?", (EXPECTED_GOALS_SCHEMA,))
        conn.commit()
        conn.close()
        return {"status": "repaired", "action": "recreated"}
    except Exception as e:
        return {"status": "failed", "detail": str(e)}

def repair_config_db():
    """Attempt to repair or recreate agent_config.db."""
    try:
        if CONFIG_DB.exists():
            os.remove(str(CONFIG_DB))
        conn = sqlite3.connect(str(CONFIG_DB))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, agent_name TEXT, config_json TEXT, version INTEGER, created_at TEXT)")
        cursor.execute("PRAGMA schema_version = ?", (EXPECTED_CONFIG_SCHEMA,))
        conn.commit()
        conn.close()
        return {"status": "repaired", "action": "recreated"}
    except Exception as e:
        return {"status": "failed", "detail": str(e)}

def run_verification():
    """Run all verifications and return a report."""
    report = {
        "goals_db": verify_goals_db(),
        "config_db": verify_config_db(),
        "checkpoints": verify_checkpoints()
    }
    return report

def run_repair():
    """Attempt to repair any issues found."""
    repair_actions = []
    goals_status = verify_goals_db()
    if goals_status["status"] in ("missing", "corrupt", "schema_mismatch"):
        repair_actions.append({"component": "goals_db", "result": repair_goals_db()})
    config_status = verify_config_db()
    if config_status["status"] in ("missing", "corrupt", "schema_mismatch"):
        repair_actions.append({"component": "config_db", "result": repair_config_db()})
    # For checkpoints, we only report; repair would require rollback logic
    return repair_actions

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "repair":
        result = run_repair()
        print(json.dumps(result, indent=2))
    else:
        report = run_verification()
        print(json.dumps(report, indent=2))
