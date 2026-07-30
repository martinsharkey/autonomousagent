import json
import hashlib
import hmac
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("checkpoints")
SECRET_KEY = os.environ.get("STATE_HMAC_KEY", "default-dev-key").encode()

def compute_hmac(data: bytes) -> str:
    return hmac.new(SECRET_KEY, data, hashlib.sha256).hexdigest()

def verify_checkpoint(checkpoint_path: Path) -> bool:
    """Verify the integrity of a checkpoint file using HMAC."""
    try:
        with open(checkpoint_path, "rb") as f:
            raw = f.read()
        # Expect last line to be the HMAC
        lines = raw.split(b"\n")
        if len(lines) < 2:
            logger.warning(f"Checkpoint {checkpoint_path} has no HMAC.")
            return False
        data = b"\n".join(lines[:-1])
        stored_hmac = lines[-1].decode().strip()
        expected_hmac = compute_hmac(data)
        if stored_hmac != expected_hmac:
            logger.error(f"HMAC mismatch for {checkpoint_path}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error verifying checkpoint {checkpoint_path}: {e}")
        return False

def find_latest_valid_checkpoint() -> Path | None:
    """Find the most recent checkpoint that passes integrity verification."""
    if not CHECKPOINT_DIR.exists():
        return None
    checkpoints = sorted(CHECKPOINT_DIR.glob("*.ckpt"), key=os.path.getmtime, reverse=True)
    for cp in checkpoints:
        if verify_checkpoint(cp):
            return cp
    return None

def recover_state() -> dict | None:
    """Recover state from the latest valid checkpoint."""
    latest = find_latest_valid_checkpoint()
    if latest is None:
        logger.error("No valid checkpoint found for recovery.")
        return None
    try:
        with open(latest, "r") as f:
            lines = f.read().strip().split("\n")
            state = json.loads("\n".join(lines[:-1]))
        logger.info(f"State recovered from {latest}")
        return state
    except Exception as e:
        logger.error(f"Failed to load state from {latest}: {e}")
        return None

def save_checkpoint_with_hmac(state: dict, path: Path) -> bool:
    """Save state with HMAC integrity tag."""
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        data = json.dumps(state, indent=2).encode()
        hmac_tag = compute_hmac(data)
        with open(path, "wb") as f:
            f.write(data + b"\n" + hmac_tag.encode())
        logger.info(f"Checkpoint saved with HMAC to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save checkpoint {path}: {e}")
        return False

def list_corrupted_checkpoints() -> list[Path]:
    """List all checkpoints that fail integrity verification."""
    if not CHECKPOINT_DIR.exists():
        return []
    corrupted = []
    for cp in CHECKPOINT_DIR.glob("*.ckpt"):
        if not verify_checkpoint(cp):
            corrupted.append(cp)
    return corrupted
