#!/usr/bin/env python3
"""State recovery tool: verifies checkpoints and restores from the most recent valid snapshot."""
import json
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = "checkpoints"

def verify_checkpoint(path: str) -> bool:
    """Check if a checkpoint file is valid JSON and contains required keys."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        required_keys = ['state', 'timestamp', 'version']
        return all(key in data for key in required_keys)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Checkpoint verification failed for {path}: {e}")
        return False

def find_latest_valid_checkpoint() -> Optional[str]:
    """Find the most recent valid checkpoint file."""
    if not os.path.isdir(CHECKPOINT_DIR):
        logger.warning(f"Checkpoint directory {CHECKPOINT_DIR} does not exist.")
        return None
    checkpoints = sorted(
        [f for f in os.listdir(CHECKPOINT_DIR) if f.endswith('.json')],
        reverse=True
    )
    for cp in checkpoints:
        path = os.path.join(CHECKPOINT_DIR, cp)
        if verify_checkpoint(path):
            logger.info(f"Found valid checkpoint: {path}")
            return path
    logger.error("No valid checkpoint found.")
    return None

def restore_state(checkpoint_path: str) -> Optional[Dict[str, Any]]:
    """Load and return the state from a checkpoint file."""
    try:
        with open(checkpoint_path, 'r') as f:
            data = json.load(f)
        logger.info(f"State restored from {checkpoint_path}")
        return data['state']
    except Exception as e:
        logger.error(f"Failed to restore state from {checkpoint_path}: {e}")
        return None

def recover() -> Optional[Dict[str, Any]]:
    """Main recovery function: find latest valid checkpoint and restore state."""
    logger.info("Starting state recovery...")
    cp_path = find_latest_valid_checkpoint()
    if cp_path is None:
        return None
    state = restore_state(cp_path)
    if state is None:
        return None
    logger.info("State recovery completed successfully.")
    return state

if __name__ == "__main__":
    state = recover()
    if state:
        print("Recovery successful.")
    else:
        print("Recovery failed.")
