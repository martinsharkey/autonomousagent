#!/usr/bin/env python3
"""State recovery tool for durable local state.

Verifies checkpoint integrity and restores the last consistent state.
"""

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

# Default checkpoint directory (can be overridden via env var)
DEFAULT_CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_DIR = Path(os.getenv("CHECKPOINT_DIR", DEFAULT_CHECKPOINT_DIR))

# Required files in a valid checkpoint
REQUIRED_FILES = ["state.json", "goals.db", "agent_config.json"]


def verify_checkpoint(checkpoint_path: Path) -> bool:
    """Check if a checkpoint is complete and valid."""
    if not checkpoint_path.is_dir():
        return False
    for fname in REQUIRED_FILES:
        fpath = checkpoint_path / fname
        if not fpath.is_file():
            return False
        # Basic integrity: non-empty and valid JSON for JSON files
        if fname.endswith(".json"):
            try:
                with open(fpath, "r") as f:
                    json.load(f)
            except (json.JSONDecodeError, OSError):
                return False
        elif fname.endswith(".db"):
            # Check SQLite integrity
            try:
                conn = sqlite3.connect(fpath)
                result = conn.execute("PRAGMA integrity_check").fetchone()
                conn.close()
                if result[0] != "ok":
                    return False
            except sqlite3.Error:
                return False
    return True


def list_checkpoints() -> list:
    """Return sorted list of checkpoint directories by modification time."""
    if not CHECKPOINT_DIR.exists():
        return []
    checkpoints = [p for p in CHECKPOINT_DIR.iterdir() if p.is_dir()]
    checkpoints.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return checkpoints


def restore_checkpoint(checkpoint_path: Path, target_dir: Path) -> bool:
    """Restore files from checkpoint to target directory."""
    try:
        for fname in REQUIRED_FILES:
            src = checkpoint_path / fname
            dst = target_dir / fname
            if src.exists():
                shutil.copy2(src, dst)
        return True
    except (OSError, shutil.Error):
        return False


def recover() -> dict:
    """Main recovery routine.

    Returns a dict with status and details.
    """
    result = {
        "status": "no_checkpoint",
        "restored_from": None,
        "message": "No valid checkpoint found.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    checkpoints = list_checkpoints()
    if not checkpoints:
        return result

    # Find the most recent valid checkpoint
    for cp in checkpoints:
        if verify_checkpoint(cp):
            # Restore to current working directory (or a specified target)
            target = Path(os.getenv("STATE_TARGET_DIR", "."))
            if restore_checkpoint(cp, target):
                result["status"] = "restored"
                result["restored_from"] = str(cp)
                result["message"] = f"Restored from checkpoint: {cp.name}"
                return result
            else:
                result["status"] = "restore_failed"
                result["message"] = f"Failed to restore from checkpoint: {cp.name}"
                return result

    result["status"] = "corrupt"
    result["message"] = "All checkpoints are corrupt or incomplete."
    return result


if __name__ == "__main__":
    print(json.dumps(recover(), indent=2))
