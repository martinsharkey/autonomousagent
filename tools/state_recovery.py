import sqlite3
import json
import os
from pathlib import Path

def validate_and_repair_state():
    """Check and repair durable local state files."""
    state_dir = Path("state")
    if not state_dir.exists():
        state_dir.mkdir(parents=True, exist_ok=True)
        return {"status": "created", "details": "State directory created."}
    
    issues = []
    repairs = []
    
    # Validate goals.db
    goals_db = state_dir / "goals.db"
    if goals_db.exists():
        try:
            conn = sqlite3.connect(str(goals_db))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM goals")
            count = cursor.fetchone()[0]
            conn.close()
        except Exception as e:
            issues.append(f"goals.db corruption: {e}")
            # Attempt repair by reinitializing
            try:
                os.remove(str(goals_db))
                conn = sqlite3.connect(str(goals_db))
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, description TEXT, status TEXT, created_at TEXT)")
                conn.commit()
                conn.close()
                repairs.append("goals.db reinitialized")
            except Exception as repair_err:
                issues.append(f"Failed to repair goals.db: {repair_err}")
    
    # Validate checkpoints
    checkpoint_dir = state_dir / "checkpoints"
    if checkpoint_dir.exists():
        for cp_file in checkpoint_dir.glob("*.json"):
            try:
                with open(cp_file, 'r') as f:
                    json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                issues.append(f"Corrupted checkpoint {cp_file.name}: {e}")
                try:
                    os.remove(str(cp_file))
                    repairs.append(f"Removed corrupted checkpoint {cp_file.name}")
                except Exception as repair_err:
                    issues.append(f"Failed to remove {cp_file.name}: {repair_err}")
    
    # Validate agent_config.json
    config_file = state_dir / "agent_config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            issues.append(f"agent_config.json corruption: {e}")
            try:
                # Restore default config
                default_config = {"version": 1, "config": {}}
                with open(config_file, 'w') as f:
                    json.dump(default_config, f)
                repairs.append("agent_config.json reset to default")
            except Exception as repair_err:
                issues.append(f"Failed to repair agent_config.json: {repair_err}")
    
    return {"status": "ok" if not issues else "repaired", "issues": issues, "repairs": repairs}

if __name__ == "__main__":
    result = validate_and_repair_state()
    print(json.dumps(result, indent=2))
