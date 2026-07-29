#!/usr/bin/env python3
"""State integrity verification and repair tool for durable local state."""

import sqlite3
import hashlib
import hmac
import json
import os
from pathlib import Path

# Paths (adjust as needed)
GOALS_DB = Path("data/goals.db")
CONFIG_DB = Path("data/agent_config.db")
AUDIT_LOG = Path("data/audit.log")
SECRET_KEY = os.environ.get("HMAC_SECRET", "default-dev-key")

def verify_goals_db() -> dict:
    """Check goals DB integrity and consistency."""
    result = {"status": "ok", "issues": []}
    if not GOALS_DB.exists():
        result["status"] = "missing"
        result["issues"].append("Goals DB file not found")
        return result
    try:
        conn = sqlite3.connect(str(GOALS_DB))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            result["status"] = "corrupt"
            result["issues"].append(f"Integrity check failed: {integrity}")
        cursor.execute("SELECT COUNT(*) FROM goals")
        count = cursor.fetchone()[0]
        result["goal_count"] = count
        conn.close()
    except Exception as e:
        result["status"] = "error"
        result["issues"].append(str(e))
    return result

def verify_config_db() -> dict:
    """Check config DB integrity."""
    result = {"status": "ok", "issues": []}
    if not CONFIG_DB.exists():
        result["status"] = "missing"
        result["issues"].append("Config DB file not found")
        return result
    try:
        conn = sqlite3.connect(str(CONFIG_DB))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            result["status"] = "corrupt"
            result["issues"].append(f"Integrity check failed: {integrity}")
        cursor.execute("SELECT COUNT(*) FROM config")
        count = cursor.fetchone()[0]
        result["config_count"] = count
        conn.close()
    except Exception as e:
        result["status"] = "error"
        result["issues"].append(str(e))
    return result

def verify_audit_log() -> dict:
    """Verify HMAC signatures in audit log."""
    result = {"status": "ok", "issues": [], "entries_checked": 0}
    if not AUDIT_LOG.exists():
        result["status"] = "missing"
        result["issues"].append("Audit log file not found")
        return result
    try:
        with open(AUDIT_LOG, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    stored_hmac = entry.pop("hmac", None)
                    if stored_hmac is None:
                        result["issues"].append("Entry missing HMAC")
                        continue
                    # Recompute HMAC
                    serialized = json.dumps(entry, sort_keys=True)
                    expected_hmac = hmac.new(
                        SECRET_KEY.encode(),
                        serialized.encode(),
                        hashlib.sha256
                    ).hexdigest()
                    if not hmac.compare_digest(stored_hmac, expected_hmac):
                        result["issues"].append("HMAC mismatch detected")
                        result["status"] = "corrupt"
                    result["entries_checked"] += 1
                except (json.JSONDecodeError, KeyError) as e:
                    result["issues"].append(f"Parse error: {e}")
                    result["status"] = "corrupt"
    except Exception as e:
        result["status"] = "error"
        result["issues"].append(str(e))
    return result

def repair_goals_db() -> dict:
    """Attempt to repair goals DB by rebuilding."""
    result = {"status": "ok", "message": ""}
    try:
        # Simple repair: dump and reload
        conn = sqlite3.connect(str(GOALS_DB))
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        conn.close()
        result["message"] = "Goals DB vacuumed successfully"
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
    return result

def repair_config_db() -> dict:
    """Attempt to repair config DB."""
    result = {"status": "ok", "message": ""}
    try:
        conn = sqlite3.connect(str(CONFIG_DB))
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        conn.close()
        result["message"] = "Config DB vacuumed successfully"
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
    return result

def run_integrity_check(repair: bool = False) -> dict:
    """Run full integrity check, optionally repair."""
    results = {
        "goals_db": verify_goals_db(),
        "config_db": verify_config_db(),
        "audit_log": verify_audit_log()
    }
    if repair:
        if results["goals_db"]["status"] in ("corrupt", "error"):
            results["goals_db_repair"] = repair_goals_db()
        if results["config_db"]["status"] in ("corrupt", "error"):
            results["config_db_repair"] = repair_config_db()
    return results

if __name__ == "__main__":
    import sys
    repair_flag = "--repair" in sys.argv
    result = run_integrity_check(repair=repair_flag)
    print(json.dumps(result, indent=2))
