#!/usr/bin/env python3
"""State recovery tool: verifies and repairs durable local state (SQLite, config files) using checksums and schema validation."""
import hashlib
import json
import os
import sqlite3
import shutil
from pathlib import Path

# Expected checksums for critical state files (stored in a manifest)
MANIFEST_PATH = Path("state_manifest.json")
BACKUP_DIR = Path("state_backups")

def load_manifest():
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    return {}

def save_manifest(manifest):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

def compute_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def verify_sqlite_integrity(db_path):
    """Run PRAGMA integrity_check on SQLite database."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        return result[0] == "ok"
    except Exception as e:
        return False

def repair_sqlite(db_path):
    """Attempt to repair a corrupted SQLite database using backup."""
    backup_path = BACKUP_DIR / f"{db_path.name}.backup"
    if backup_path.exists():
        shutil.copy2(backup_path, db_path)
        return True
    return False

def verify_config_file(filepath):
    """Verify JSON/YAML config file is valid."""
    try:
        with open(filepath, "r") as f:
            content = f.read()
        # Try parsing as JSON
        json.loads(content)
        return True
    except (json.JSONDecodeError, Exception):
        return False

def repair_config(filepath):
    """Restore config from backup if available."""
    backup_path = BACKUP_DIR / f"{filepath.name}.backup"
    if backup_path.exists():
        shutil.copy2(backup_path, filepath)
        return True
    return False

def run_state_recovery():
    """Main recovery routine: verify all tracked state files and repair if needed."""
    manifest = load_manifest()
    recovery_log = []
    for filepath_str, expected_checksum in manifest.items():
        filepath = Path(filepath_str)
        if not filepath.exists():
            recovery_log.append(f"Missing: {filepath_str}")
            continue
        current_checksum = compute_checksum(filepath)
        if current_checksum != expected_checksum:
            # Potential corruption
            if filepath.suffix == ".db":
                if not verify_sqlite_integrity(filepath):
                    if repair_sqlite(filepath):
                        recovery_log.append(f"Repaired SQLite: {filepath_str}")
                    else:
                        recovery_log.append(f"Failed to repair SQLite: {filepath_str}")
            elif filepath.suffix in [".json", ".yaml", ".yml"]:
                if not verify_config_file(filepath):
                    if repair_config(filepath):
                        recovery_log.append(f"Repaired config: {filepath_str}")
                    else:
                        recovery_log.append(f"Failed to repair config: {filepath_str}")
            else:
                recovery_log.append(f"Checksum mismatch (no repair strategy): {filepath_str}")
        else:
            recovery_log.append(f"OK: {filepath_str}")
    return recovery_log

def update_manifest():
    """Update manifest with current checksums for all tracked state files."""
    tracked = [
        "core/goals.py",
        "core/agent_config.py",
        "core/health.py",
        "governance/audit_log.py",
        "governance/keys.py",
    ]
    manifest = {}
    for path in tracked:
        if os.path.exists(path):
            manifest[path] = compute_checksum(path)
    save_manifest(manifest)
    return manifest

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        update_manifest()
        print("Manifest updated.")
    else:
        log = run_state_recovery()
        for entry in log:
            print(entry)
