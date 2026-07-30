#!/usr/bin/env python3
"""State recovery tool: validates checkpoints and restores from latest valid snapshot."""
import json
import os
import hashlib
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = "checkpoints"
CHECKSUM_FILE = "checkpoint_checksums.json"

def load_checksums() -> Dict[str, str]:
    """Load checksums from file."""
    if not os.path.exists(CHECKSUM_FILE):
        return {}
    with open(CHECKSUM_FILE, "r") as f:
        return json.load(f)

def save_checksums(checksums: Dict[str, str]) -> None:
    """Save checksums to file."""
    with open(CHECKSUM_FILE, "w") as f:
        json.dump(checksums, f, indent=2)

def compute_checksum(filepath: str) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def validate_checkpoint(checkpoint_path: str) -> bool:
    """Validate a checkpoint file using stored checksum."""
    if not os.path.exists(checkpoint_path):
        logger.error(f"Checkpoint not found: {checkpoint_path}")
        return False
    checksums = load_checksums()
    expected = checksums.get(checkpoint_path)
    if expected is None:
        logger.warning(f"No checksum for {checkpoint_path}, computing and storing.")
        actual = compute_checksum(checkpoint_path)
        checksums[checkpoint_path] = actual
        save_checksums(checksums)
        return True
    actual = compute_checksum(checkpoint_path)
    if actual != expected:
        logger.error(f"Checksum mismatch for {checkpoint_path}: expected {expected}, got {actual}")
        return False
    logger.info(f"Checkpoint {checkpoint_path} validated.")
    return True

def find_latest_valid_checkpoint() -> Optional[str]:
    """Find the latest valid checkpoint in the checkpoint directory."""
    if not os.path.isdir(CHECKPOINT_DIR):
        logger.warning(f"Checkpoint directory {CHECKPOINT_DIR} not found.")
        return None
    checkpoints = sorted([f for f in os.listdir(CHECKPOINT_DIR) if f.endswith(".json")], reverse=True)
    for cp in checkpoints:
        cp_path = os.path.join(CHECKPOINT_DIR, cp)
        if validate_checkpoint(cp_path):
            return cp_path
    return None

def restore_state(checkpoint_path: str) -> Optional[Dict[str, Any]]:
    """Restore state from a checkpoint file."""
    try:
        with open(checkpoint_path, "r") as f:
            state = json.load(f)
        logger.info(f"State restored from {checkpoint_path}")
        return state
    except Exception as e:
        logger.error(f"Failed to restore state from {checkpoint_path}: {e}")
        return None

def recover() -> Optional[Dict[str, Any]]:
    """Main recovery function: find latest valid checkpoint and restore state."""
    latest = find_latest_valid_checkpoint()
    if latest is None:
        logger.error("No valid checkpoint found. Starting fresh.")
        return None
    state = restore_state(latest)
    if state is None:
        logger.error("Failed to restore state from latest checkpoint.")
        return None
    return state

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    state = recover()
    if state:
        print("Recovery successful.")
    else:
        print("Recovery failed.")
