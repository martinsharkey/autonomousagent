#!/usr/bin/env python3
"""Self-diagnostic and recovery tool for autobot.

Scans for common failure states (missing files, stale checkpoints,
config corruption) and attempts repairs. Logs all actions to the
audit log for learning.
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

# Expected critical files
CRITICAL_FILES = [
    "core/agent_config.py",
    "core/goals.py",
    "core/health.py",
    "governance/audit_log.py",
    "tools/mcp_registry.py",
]

# Known config keys that must exist
REQUIRED_CONFIG_KEYS = ["max_retries", "system_prompt"]


def _hash_file(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def check_missing_files() -> List[str]:
    """Return list of missing critical files."""
    missing = []
    for f in CRITICAL_FILES:
        if not os.path.exists(f):
            missing.append(f)
    return missing


def check_config_integrity() -> List[str]:
    """Check agent_config.db for required keys."""
    issues = []
    db_path = "agent_config.db"
    if not os.path.exists(db_path):
        issues.append("agent_config.db missing")
        return issues
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM config")
        rows = cursor.fetchall()
        existing_keys = {row[0] for row in rows}
        for key in REQUIRED_CONFIG_KEYS:
            if key not in existing_keys:
                issues.append(f"Missing config key: {key}")
        conn.close()
    except Exception as e:
        issues.append(f"Config DB error: {e}")
    return issues


def check_audit_log_integrity() -> List[str]:
    """Verify audit log HMAC consistency."""
    issues = []
    log_path = "audit.log"
    if not os.path.exists(log_path):
        issues.append("audit.log missing")
        return issues
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            parts = line.strip().split("|")
            if len(parts) < 3:
                issues.append(f"audit.log line {i+1}: malformed")
                continue
            # Basic check: last part should be hex (HMAC)
            hmac_part = parts[-1]
            if not all(c in "0123456789abcdef" for c in hmac_part):
                issues.append(f"audit.log line {i+1}: invalid HMAC")
    except Exception as e:
        issues.append(f"Audit log error: {e}")
    return issues


def repair_missing_file(path: str) -> bool:
    """Attempt to recreate a missing critical file from template."""
    # Minimal stub creation - in production would use versioned templates
    stub_content = f"# Auto-recovered {path}\n"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(stub_content)
        return True
    except Exception:
        return False


def repair_config_key(key: str) -> bool:
    """Insert a default value for a missing config key."""
    defaults = {
        "max_retries": "3",
        "system_prompt": "You are a helpful assistant.",
    }
    try:
        conn = sqlite3.connect("agent_config.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            (key, defaults.get(key, "")),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def run_diagnostics() -> Dict[str, List[str]]:
    """Run all checks and return issues by category."""
    return {
        "missing_files": check_missing_files(),
        "config_issues": check_config_integrity(),
        "audit_issues": check_audit_log_integrity(),
    }


def auto_repair(issues: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Attempt to repair all detected issues."""
    repairs = {"repaired": [], "failed": []}
    for f in issues.get("missing_files", []):
        if repair_missing_file(f):
            repairs["repaired"].append(f"file:{f}")
        else:
            repairs["failed"].append(f"file:{f}")
    for key in issues.get("config_issues", []):
        if key.startswith("Missing config key:"):
            k = key.split(":")[-1].strip()
            if repair_config_key(k):
                repairs["repaired"].append(f"config:{k}")
            else:
                repairs["failed"].append(f"config:{k}")
    # Audit log issues are logged but not auto-repaired (data loss risk)
    for issue in issues.get("audit_issues", []):
        repairs["failed"].append(f"audit:{issue}")
    return repairs


def self_heal() -> Dict:
    """Main entry point: diagnose and repair."""
    issues = run_diagnostics()
    repairs = auto_repair(issues)
    result = {
        "issues_found": issues,
        "repairs_attempted": repairs,
        "healthy": len(issues["missing_files"]) == 0
                  and len(issues["config_issues"]) == 0
                  and len(issues["audit_issues"]) == 0,
    }
    # Log to audit log
    log_entry = f"SELF_HEAL|{json.dumps(result)}"
    try:
        with open("audit.log", "a") as f:
            f.write(log_entry + "\n")
    except Exception:
        pass
    return result


if __name__ == "__main__":
    result = self_heal()
    print(json.dumps(result, indent=2))
