#!/usr/bin/env python3
"""State integrity checker and recovery tool."""
import json
import os
import glob
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = "checkpoints"

def validate_checkpoint(path: str) -> bool:
    """Validate a checkpoint file's integrity."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        # Basic structure checks
        if not isinstance(data, dict):
            logger.warning(f"Checkpoint {path} is not a dict")
            return False
        if "timestamp" not in data:
            logger.warning(f"Checkpoint {path} missing timestamp")
            return False
        if "state" not in data:
            logger.warning(f"Checkpoint {path} missing state")
            return False
        # Optional: check for required keys in state
        state = data["state"]
        if not isinstance(state, dict):
            logger.warning(f"Checkpoint {path} state is not a dict")
            return False
        return True
    except (json.JSONDecodeError, IOError, Exception) as e:
        logger.error(f"Checkpoint {path} validation failed: {e}")
        return False

def find_latest_valid_checkpoint() -> str | None:
    """Find the most recent valid checkpoint."""
    if not os.path.isdir(CHECKPOINT_DIR):
        logger.error(f"Checkpoint directory {CHECKPOINT_DIR} not found")
        return None
    pattern = os.path.join(CHECKPOINT_DIR, "*.json")
    files = glob.glob(pattern)
    if not files:
        logger.warning("No checkpoint files found")
        return None
    # Sort by modification time descending
    files.sort(key=os.path.getmtime, reverse=True)
    for f in files:
        if validate_checkpoint(f):
            logger.info(f"Found valid checkpoint: {f}")
            return f
    logger.error("No valid checkpoint found")
    return None

def recover_from_checkpoint(path: str) -> dict | None:
    """Load state from a valid checkpoint."""
    if not validate_checkpoint(path):
        logger.error(f"Cannot recover from invalid checkpoint: {path}")
        return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        logger.info(f"Recovered state from {path}")
        return data["state"]
    except Exception as e:
        logger.error(f"Recovery failed from {path}: {e}")
        return None

def run_integrity_check() -> dict:
    """Run full integrity check and return report."""
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "checkpoint_dir": CHECKPOINT_DIR,
        "total_checkpoints": 0,
        "valid_checkpoints": 0,
        "invalid_checkpoints": 0,
        "latest_valid": None,
        "recovery_possible": False
    }
    if not os.path.isdir(CHECKPOINT_DIR):
        report["error"] = f"Directory {CHECKPOINT_DIR} not found"
        return report
    pattern = os.path.join(CHECKPOINT_DIR, "*.json")
    files = glob.glob(pattern)
    report["total_checkpoints"] = len(files)
    for f in files:
        if validate_checkpoint(f):
            report["valid_checkpoints"] += 1
        else:
            report["invalid_checkpoints"] += 1
    latest = find_latest_valid_checkpoint()
    if latest:
        report["latest_valid"] = latest
        report["recovery_possible"] = True
    return report

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        report = run_integrity_check()
        print(json.dumps(report, indent=2))
    elif len(sys.argv) > 2 and sys.argv[1] == "recover":
        state = recover_from_checkpoint(sys.argv[2])
        if state:
            print(json.dumps(state, indent=2))
        else:
            print("Recovery failed")
    else:
        print("Usage: state_integrity.py check | recover <path>")
