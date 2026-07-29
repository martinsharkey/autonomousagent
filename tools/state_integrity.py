#!/usr/bin/env python3
"""State integrity verification and repair tool for durable local state."""
import sqlite3
import hashlib
import json
import os
from pathlib import Path

DB_PATHS = {
    "goals": "data/goals.db",
    "config": "data/agent_config.db",
    "audit": "data/audit_log.db",
}

def verify_table_integrity(db_path: str) -> dict:
    """Run integrity check on a SQLite database."""
    result = {"db": db_path, "ok": False, "errors": []}
    if not os.path.exists(db_path):
        result["errors"].append("Database file not found")
        return result
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        rows = cursor.fetchall()
        if all(row[0] == "ok" for row in rows):
            result["ok"] = True
        else:
            result["errors"] = [row[0] for row in rows if row[0] != "ok"]
        conn.close()
    except Exception as e:
        result["errors"].append(str(e))
    return result

def reindex_database(db_path: str) -> bool:
    """Reindex all tables in a database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("REINDEX")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def compute_state_checksum(db_path: str) -> str:
    """Compute SHA256 checksum of the database file."""
    sha = hashlib.sha256()
    try:
        with open(db_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return ""

def run_integrity_check() -> dict:
    """Run full state integrity check across all durable stores."""
    results = {}
    for name, path in DB_PATHS.items():
        full_path = os.path.join(os.getcwd(), path)
        integrity = verify_table_integrity(full_path)
        checksum = compute_state_checksum(full_path)
        results[name] = {
            "integrity": integrity,
            "checksum": checksum,
            "exists": os.path.exists(full_path),
        }
    return results

def repair_state(db_name: str) -> dict:
    """Attempt to repair a specific state store by reindexing."""
    if db_name not in DB_PATHS:
        return {"ok": False, "error": f"Unknown database: {db_name}"}
    full_path = os.path.join(os.getcwd(), DB_PATHS[db_name])
    if not os.path.exists(full_path):
        return {"ok": False, "error": "Database file not found"}
    success = reindex_database(full_path)
    return {"ok": success, "db": db_name}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "repair":
        db = sys.argv[2] if len(sys.argv) > 2 else "all"
        if db == "all":
            for name in DB_PATHS:
                print(json.dumps(repair_state(name)))
        else:
            print(json.dumps(repair_state(db)))
    else:
        print(json.dumps(run_integrity_check(), indent=2))
