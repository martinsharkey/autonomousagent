import sqlite3
import json
import os
from pathlib import Path

class StateRecoveryTool:
    """Tool to verify and repair durable local state (SQLite checkpoints)."""

    def __init__(self, db_path: str = "data/checkpoints.db"):
        self.db_path = db_path

    def verify_integrity(self) -> dict:
        """Run PRAGMA integrity_check on the SQLite database."""
        if not os.path.exists(self.db_path):
            return {"status": "missing", "message": "Database file not found."}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchall()
            conn.close()
            if all(row[0] == "ok" for row in result):
                return {"status": "ok", "message": "Integrity check passed."}
            else:
                return {"status": "corrupt", "details": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_checkpoints(self) -> list:
        """List all checkpoint entries in the database."""
        if not os.path.exists(self.db_path):
            return []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, timestamp, status FROM checkpoints ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            conn.close()
            return [{"name": r[0], "timestamp": r[1], "status": r[2]} for r in rows]
        except Exception:
            return []

    def recover_latest(self) -> dict:
        """Attempt to recover the latest valid checkpoint."""
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return {"status": "no_checkpoints", "message": "No checkpoints available for recovery."}
        # Find the most recent checkpoint with status 'valid'
        valid = [c for c in checkpoints if c["status"] == "valid"]
        if not valid:
            return {"status": "no_valid", "message": "No valid checkpoint found."}
        latest = valid[0]
        # In a real implementation, load the checkpoint data and restore state
        return {"status": "recovered", "checkpoint": latest}

    def repair(self) -> dict:
        """Attempt to repair a corrupted database by dumping and recreating."""
        if not os.path.exists(self.db_path):
            return {"status": "missing", "message": "Cannot repair missing database."}
        try:
            # Attempt to dump recoverable data
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, timestamp, data FROM checkpoints")
            rows = cursor.fetchall()
            conn.close()
            # Backup original
            backup_path = self.db_path + ".backup"
            os.rename(self.db_path, backup_path)
            # Create new database and insert recovered rows
            new_conn = sqlite3.connect(self.db_path)
            new_cursor = new_conn.cursor()
            new_cursor.execute("CREATE TABLE IF NOT EXISTS checkpoints (name TEXT PRIMARY KEY, timestamp TEXT, data TEXT, status TEXT DEFAULT 'valid')")
            for row in rows:
                new_cursor.execute("INSERT OR REPLACE INTO checkpoints (name, timestamp, data, status) VALUES (?, ?, ?, 'valid')", (row[0], row[1], row[2]))
            new_conn.commit()
            new_conn.close()
            return {"status": "repaired", "recovered_count": len(rows)}
        except Exception as e:
            return {"status": "failed", "message": str(e)}
