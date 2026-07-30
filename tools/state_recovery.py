import json
import os
import glob
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = "checkpoints"
SNAPSHOT_DIR = "snapshots"

def validate_checkpoint(path: str) -> bool:
    """Check if a checkpoint file is valid JSON and has required fields."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return isinstance(data, dict) and "state" in data
    except (json.JSONDecodeError, IOError, TypeError):
        return False

def find_latest_valid_checkpoint() -> Optional[str]:
    """Find the most recent valid checkpoint file."""
    pattern = os.path.join(CHECKPOINT_DIR, "*.json")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    for f in files:
        if validate_checkpoint(f):
            return f
    return None

def find_latest_snapshot() -> Optional[str]:
    """Find the most recent snapshot file."""
    pattern = os.path.join(SNAPSHOT_DIR, "*.json")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return files[0] if files else None

def recover_state() -> Dict[str, Any]:
    """Attempt to recover state from checkpoint or snapshot."""
    checkpoint = find_latest_valid_checkpoint()
    if checkpoint:
        logger.info(f"Recovering from checkpoint: {checkpoint}")
        with open(checkpoint, 'r') as f:
            return json.load(f)
    snapshot = find_latest_snapshot()
    if snapshot:
        logger.info(f"Recovering from snapshot: {snapshot}")
        with open(snapshot, 'r') as f:
            return json.load(f)
    logger.error("No valid checkpoint or snapshot found.")
    return {}

def main():
    """CLI entry point for manual recovery."""
    state = recover_state()
    if state:
        print("Recovery successful. State keys:", list(state.keys()))
    else:
        print("Recovery failed.")

if __name__ == "__main__":
    main()
