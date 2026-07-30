#!/usr/bin/env python3
"""State integrity verification and repair tool for durable local state."""
import sqlite3
import hashlib
import json
import os
from pathlib import Path

CHECKSUMS_FILE = "state_checksums.json"
BACKUP_DIR = "backups/"

def compute_checksum(db_path: str) -> str:
    """Compute SHA256 checksum of a SQLite database."""
    hasher = hashlib.sha256()
    with open(db_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def load_checksums() -> dict:
    """Load stored checksums from file."""
    if os.path.exists(CHECKSUMS_FILE):
        with open(CHECKSUMS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_checksums(checksums: dict):
    """Save checksums to file."""
    with open(CHECKSUMS_FILE, "w") as f:
        json.dump(checksums, f, indent=2)

def verify_state(db_path: str, name: str) -> dict:
    """Verify integrity of a state database."""
    result = {"name": name, "path": db_path, "valid": False, "issues": []}
    if not os.path.exists(db_path):
        result["issues"].append("Database file not found")
        return result
    # Check file size
    size = os.path.getsize(db_path)
    if size == 0:
        result["issues"].append("Database file is empty")
        return result
    # Try opening and running integrity check
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        if integrity_result != "ok":
            result["issues"].append(f"Integrity check failed: {integrity_result}")
        else:
            result["valid"] = True
        conn.close()
    except Exception as e:
        result["issues"].append(f"SQLite error: {str(e)}")
    # Compare checksum
    stored = load_checksums()
    if name in stored:
        current_checksum = compute_checksum(db_path)
        if current_checksum != stored[name]:
            result["issues"].append("Checksum mismatch - state may have changed unexpectedly")
            result["valid"] = False
    else:
        # First time, store checksum
        stored[name] = compute_checksum(db_path)
        save_checksums(stored)
    return result

def repair_from_backup(db_path: str, backup_path: str) -> bool:
    """Repair a database by restoring from a backup."""
    if not os.path.exists(backup_path):
        return False
    try:
        # Create a backup of the corrupted file
        corrupt_backup = db_path + ".corrupt"
        os.rename(db_path, corrupt_backup)
        # Restore from backup
        import shutil
        shutil.copy2(backup_path, db_path)
        return True
    except Exception:
        return False

def run_integrity_check() -> dict:
    """Run full state integrity check across all known state files."""
    state_files = {
        "goal_store": "data/goals.db",
        "agent_config": "data/agent_config.db",
        "audit_log": "data/audit_log.db"
    }
    results = {}
    all_valid = True
    for name, path in state_files.items():
        result = verify_state(path, name)
        results[name] = result
        if not result["valid"]:
            all_valid = False
            # Attempt repair from backup
            backup_path = os.path.join(BACKUP_DIR, f"{name}.backup")
            if os.path.exists(backup_path):
                success = repair_from_backup(path, backup_path)
                results[name]["repaired"] = success
                if success:
                    results[name]["valid"] = True
                    results[name]["issues"].append("Repaired from backup")
    return {"all_valid": all_valid, "results": results}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        result = run_integrity_check()
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python tools/state_integrity.py check")
