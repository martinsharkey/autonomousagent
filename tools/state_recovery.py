#!/usr/bin/env python3
"""State recovery tool: validates and repairs durable local state."""
import json
import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Paths (adjust as needed)
CHECKPOINT_DIR = Path("checkpoints")
GOALS_DB = Path("goals.db")
CONFIG_FILE = Path("agent_config.json")

def validate_checkpoints() -> list:
    """Check all checkpoint files for valid JSON and required keys."""
    issues = []
    if not CHECKPOINT_DIR.exists():
        logger.warning("Checkpoint directory missing, creating.")
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        return issues
    for f in CHECKPOINT_DIR.iterdir():
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text())
                if "state" not in data:
                    issues.append(f"{f.name}: missing 'state' key")
            except (json.JSONDecodeError, ValueError) as e:
                issues.append(f"{f.name}: invalid JSON - {e}")
                # Attempt repair: reset to empty state
                try:
                    with open(f, "w") as fh:
                        json.dump({"state": {}}, fh)
                    logger.info(f"Repaired {f.name}")
                except Exception as ex:
                    logger.error(f"Failed to repair {f.name}: {ex}")
    return issues

def validate_goals_db() -> list:
    """Check goals database integrity."""
    issues = []
    if not GOALS_DB.exists():
        logger.warning("Goals database missing, creating.")
        conn = sqlite3.connect(str(GOALS_DB))
        conn.execute("CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, description TEXT, status TEXT)")
        conn.close()
        return issues
    try:
        conn = sqlite3.connect(str(GOALS_DB))
        conn.execute("SELECT 1 FROM goals LIMIT 1")
        conn.close()
    except sqlite3.DatabaseError as e:
        issues.append(f"Goals DB corrupted: {e}")
        # Attempt repair by recreating
        try:
            os.remove(str(GOALS_DB))
            conn = sqlite3.connect(str(GOALS_DB))
            conn.execute("CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, description TEXT, status TEXT)")
            conn.close()
            logger.info("Recreated goals database.")
        except Exception as ex:
            logger.error(f"Failed to repair goals DB: {ex}")
    return issues

def validate_config() -> list:
    """Check config file for valid JSON and required keys."""
    issues = []
    if not CONFIG_FILE.exists():
        logger.warning("Config file missing, creating default.")
        default_config = {"version": 1, "agent_name": "alpha_evaluator", "system_prompt": ""}
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f)
        return issues
    try:
        data = json.loads(CONFIG_FILE.read_text())
        if "version" not in data:
            issues.append("Config missing 'version' key")
    except (json.JSONDecodeError, ValueError) as e:
        issues.append(f"Config invalid: {e}")
        # Reset to default
        default_config = {"version": 1, "agent_name": "alpha_evaluator", "system_prompt": ""}
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f)
        logger.info("Reset config to default.")
    return issues

def run_recovery() -> dict:
    """Run all validations and repairs, return summary."""
    issues = {}
    issues["checkpoints"] = validate_checkpoints()
    issues["goals_db"] = validate_goals_db()
    issues["config"] = validate_config()
    total = sum(len(v) for v in issues.values())
    logger.info(f"State recovery complete: {total} issues found and repaired.")
    return {"status": "ok" if total == 0 else "repaired", "issues": issues}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_recovery()
    print(json.dumps(result, indent=2))
