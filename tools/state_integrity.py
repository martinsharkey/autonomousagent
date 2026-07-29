#!/usr/bin/env python3
"""State integrity verifier for durable local state.

Checks and repairs checkpoints, goals, and config files.
"""
import json
import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Expected paths relative to project root
STATE_DIRS = [
    "checkpoints",
    "data",
]

REQUIRED_FILES = [
    "core/goals.py",
    "core/agent_config.py",
    "core/checkpointer.py",
]


def verify_checkpoints() -> list:
    """Verify checkpoint files exist and are valid JSON."""
    issues = []
    checkpoint_dir = Path("checkpoints")
    if not checkpoint_dir.exists():
        logger.warning("Checkpoint directory missing, creating.")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        issues.append("Created missing checkpoint directory")
        return issues
    for f in checkpoint_dir.iterdir():
        if f.suffix == ".json":
            try:
                with open(f, "r") as fp:
                    json.load(fp)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Corrupted checkpoint {f.name}: {e}")
                issues.append(f"Corrupted checkpoint {f.name}")
                # Attempt repair: reset to empty state
                try:
                    with open(f, "w") as fp:
                        json.dump({}, fp)
                    issues.append(f"Repaired checkpoint {f.name}")
                except IOError as e2:
                    logger.error(f"Failed to repair {f.name}: {e2}")
    return issues


def verify_goals_db() -> list:
    """Verify goals SQLite database integrity."""
    issues = []
    db_path = Path("data/goals.db")
    if not db_path.exists():
        logger.warning("Goals database missing, will be created on first use.")
        return issues
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result and result[0] != "ok":
            logger.error(f"Goals DB integrity check failed: {result}")
            issues.append(f"Goals DB integrity issue: {result}")
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Cannot open goals DB: {e}")
        issues.append(f"Cannot open goals DB: {e}")
    return issues


def verify_config_files() -> list:
    """Verify required config files exist."""
    issues = []
    for fpath in REQUIRED_FILES:
        p = Path(fpath)
        if not p.exists():
            logger.warning(f"Required file missing: {fpath}")
            issues.append(f"Missing required file: {fpath}")
    return issues


def run_integrity_check() -> dict:
    """Run all checks and return summary."""
    issues = []
    issues.extend(verify_checkpoints())
    issues.extend(verify_goals_db())
    issues.extend(verify_config_files())
    return {
        "status": "ok" if not issues else "issues_found",
        "issues": issues,
        "repaired": [i for i in issues if i.startswith("Repaired") or i.startswith("Created")],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_integrity_check()
    print(json.dumps(result, indent=2))
