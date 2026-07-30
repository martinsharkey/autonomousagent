#!/usr/bin/env python3
"""State recovery tool: validates checkpoints and restores from latest valid snapshot."""

import json
import hashlib
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)

def compute_checksum(data: dict) -> str:
    """Compute SHA256 checksum of serialized data."""
    serialized = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(serialized).hexdigest()

def save_checkpoint(state: dict, label: str = "latest") -> bool:
    """Save state with checksum for integrity verification."""
    try:
        checksum = compute_checksum(state)
        checkpoint = {
            "checksum": checksum,
            "state": state
        }
        path = CHECKPOINT_DIR / f"{label}.json"
        with open(path, "w") as f:
            json.dump(checkpoint, f, indent=2)
        logger.info(f"Checkpoint saved: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")
        return False

def verify_checkpoint(label: str = "latest") -> bool:
    """Verify integrity of a checkpoint by comparing checksums."""
    path = CHECKPOINT_DIR / f"{label}.json"
    if not path.exists():
        logger.warning(f"Checkpoint not found: {path}")
        return False
    try:
        with open(path, "r") as f:
            checkpoint = json.load(f)
        expected_checksum = checkpoint["checksum"]
        actual_checksum = compute_checksum(checkpoint["state"])
        if expected_checksum == actual_checksum:
            logger.info(f"Checkpoint verified: {path}")
            return True
        else:
            logger.error(f"Checkpoint corrupted: {path}")
            return False
    except Exception as e:
        logger.error(f"Error verifying checkpoint: {e}")
        return False

def restore_latest() -> dict | None:
    """Restore the latest valid checkpoint. Returns state dict or None."""
    # List all checkpoints sorted by modification time
    checkpoints = sorted(CHECKPOINT_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    for cp in checkpoints:
        label = cp.stem
        if verify_checkpoint(label):
            try:
                with open(cp, "r") as f:
                    checkpoint = json.load(f)
                logger.info(f"Restored from checkpoint: {cp}")
                return checkpoint["state"]
            except Exception as e:
                logger.error(f"Failed to load checkpoint {cp}: {e}")
                continue
    logger.error("No valid checkpoint found to restore.")
    return None

def list_checkpoints() -> list[str]:
    """List all available checkpoint labels."""
    return [cp.stem for cp in CHECKPOINT_DIR.glob("*.json")]

if __name__ == "__main__":
    # CLI usage example
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        label = sys.argv[2] if len(sys.argv) > 2 else "latest"
        result = verify_checkpoint(label)
        print(f"Verification {'passed' if result else 'failed'} for {label}")
    elif len(sys.argv) > 1 and sys.argv[1] == "restore":
        state = restore_latest()
        if state:
            print("Restored state:", json.dumps(state, indent=2)[:200])
        else:
            print("No state restored.")
    else:
        print("Usage: python tools/state_recovery.py [verify|restore] [label]")
