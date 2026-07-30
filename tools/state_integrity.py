#!/usr/bin/env python3
"""State integrity checker and repair tool for durable local state."""
import sqlite3
import json
import os
import hashlib
from pathlib import Path

# Paths to critical state files
STATE_DIR = Path("state")
DB_PATHS = [
    STATE_DIR / "goals.db",
    STATE_DIR / "audit_log.db",
    STATE_DIR / "config.db",
]
CONFIG_PATHS = [
    Path("providers.yaml"),
    Path("agent_config.json"),
]

def compute_checksum(filepath):
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def check_sqlite_integrity(db_path):
    """Run SQLite integrity check and return result."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()
        return result == "ok"
    except Exception as e:
        return False, str(e)

def repair_sqlite(db_path):
    """Attempt to repair a corrupted SQLite database by dumping and recreating."""
    backup_path = db_path.with_suffix(".bak")
    try:
        # Try to dump and restore
        conn = sqlite3.connect(str(db_path))
        with open(str(backup_path), "w") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
        conn.close()
        # Recreate from dump
        os.remove(str(db_path))
        conn = sqlite3.connect(str(db_path))
        with open(str(backup_path), "r") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        os.remove(str(backup_path))
        return True
    except Exception as e:
        return False, str(e)

def validate_config_schema(config_path):
    """Validate config file schema (JSON or YAML)."""
    try:
        if config_path.suffix in [".json"]:
            with open(config_path) as f:
                data = json.load(f)
            # Basic schema check: must be dict
            if not isinstance(data, dict):
                return False, "Root must be a JSON object"
            return True, None
        elif config_path.suffix in [".yaml", ".yml"]:
            import yaml
            with open(config_path) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return False, "Root must be a mapping"
            return True, None
        else:
            return False, "Unsupported config format"
    except Exception as e:
        return False, str(e)

def run_integrity_check():
    """Run full state integrity check and return report."""
    report = {"passed": [], "failed": [], "repaired": []}
    
    # Check databases
    for db_path in DB_PATHS:
        if not db_path.exists():
            report["failed"].append(f"Missing database: {db_path}")
            continue
        ok = check_sqlite_integrity(db_path)
        if ok:
            report["passed"].append(f"Database integrity OK: {db_path}")
        else:
            report["failed"].append(f"Database integrity FAILED: {db_path}")
            # Attempt repair
            success = repair_sqlite(db_path)
            if success:
                report["repaired"].append(f"Database repaired: {db_path}")
            else:
                report["failed"].append(f"Database repair failed: {db_path}")
    
    # Check config files
    for cfg_path in CONFIG_PATHS:
        if not cfg_path.exists():
            report["failed"].append(f"Missing config: {cfg_path}")
            continue
        valid, err = validate_config_schema(cfg_path)
        if valid:
            report["passed"].append(f"Config schema OK: {cfg_path}")
        else:
            report["failed"].append(f"Config schema FAILED: {cfg_path} - {err}")
    
    return report

def main():
    report = run_integrity_check()
    print(json.dumps(report, indent=2))
    if report["failed"]:
        print("State integrity issues found. Some repairs attempted.")
    else:
        print("All state integrity checks passed.")

if __name__ == "__main__":
    main()
