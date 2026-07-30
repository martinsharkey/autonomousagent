import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

class StateRecoveryTool:
    """Validates and repairs local state databases from checkpoints."""
    
    def __init__(self, goals_db_path: str = "goals.db", config_db_path: str = "agent_config.db", checkpoint_dir: str = "checkpoints"):
        self.goals_db_path = goals_db_path
        self.config_db_path = config_db_path
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
    
    def check_integrity(self, db_path: str) -> bool:
        """Run integrity check on a SQLite database."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            return result[0] == "ok"
        except Exception as e:
            print(f"Integrity check failed for {db_path}: {e}")
            return False
    
    def get_latest_checkpoint(self) -> Optional[Path]:
        """Find the most recent checkpoint file."""
        checkpoints = sorted(self.checkpoint_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        return checkpoints[0] if checkpoints else None
    
    def restore_from_checkpoint(self, checkpoint_path: Path, target_db: str) -> bool:
        """Restore a database from a checkpoint JSON file."""
        try:
            with open(checkpoint_path, "r") as f:
                data = json.load(f)
            conn = sqlite3.connect(target_db)
            cursor = conn.cursor()
            # Recreate tables and insert data from checkpoint
            if "goals" in data:
                cursor.execute("DROP TABLE IF EXISTS goals")
                cursor.execute("CREATE TABLE goals (id INTEGER PRIMARY KEY, description TEXT, status TEXT, created_at TEXT)")
                for goal in data["goals"]:
                    cursor.execute("INSERT INTO goals VALUES (?, ?, ?, ?)", (goal["id"], goal["description"], goal["status"], goal["created_at"]))
            if "config" in data:
                cursor.execute("DROP TABLE IF EXISTS config")
                cursor.execute("CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT)")
                for key, value in data["config"].items():
                    cursor.execute("INSERT INTO config VALUES (?, ?)", (key, value))
            conn.commit()
            conn.close()
            print(f"Restored {target_db} from checkpoint {checkpoint_path}")
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            return False
    
    def recover(self) -> Dict[str, Any]:
        """Attempt to recover all state databases."""
        result = {"goals_db": False, "config_db": False, "checkpoint_used": None}
        
        # Check goals database
        if not self.check_integrity(self.goals_db_path):
            print("Goals database corrupted, attempting recovery...")
            checkpoint = self.get_latest_checkpoint()
            if checkpoint:
                result["goals_db"] = self.restore_from_checkpoint(checkpoint, self.goals_db_path)
                result["checkpoint_used"] = str(checkpoint)
            else:
                print("No checkpoint available for goals database recovery.")
        else:
            result["goals_db"] = True
        
        # Check config database
        if not self.check_integrity(self.config_db_path):
            print("Config database corrupted, attempting recovery...")
            checkpoint = self.get_latest_checkpoint()
            if checkpoint:
                result["config_db"] = self.restore_from_checkpoint(checkpoint, self.config_db_path)
                result["checkpoint_used"] = str(checkpoint)
            else:
                print("No checkpoint available for config database recovery.")
        else:
            result["config_db"] = True
        
        return result

if __name__ == "__main__":
    recovery = StateRecoveryTool()
    outcome = recovery.recover()
    print(json.dumps(outcome, indent=2))
