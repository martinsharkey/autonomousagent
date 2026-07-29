import json
import os
import hmac
import hashlib
from typing import Optional, Any

CHECKPOINT_DIR = "checkpoints"
HMAC_KEY = os.environ.get("HMAC_KEY", "default-dev-key").encode()

def verify_checkpoint(checkpoint_path: str) -> bool:
    """Verify the integrity of a checkpoint file using HMAC."""
    try:
        with open(checkpoint_path, "r") as f:
            data = json.load(f)
        stored_hmac = data.pop("hmac", None)
        if stored_hmac is None:
            return False
        computed_hmac = hmac.new(HMAC_KEY, json.dumps(data, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(stored_hmac, computed_hmac)
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        return False

def find_latest_valid_checkpoint() -> Optional[str]:
    """Find the most recent valid checkpoint."""
    if not os.path.isdir(CHECKPOINT_DIR):
        return None
    checkpoints = sorted([f for f in os.listdir(CHECKPOINT_DIR) if f.endswith(".json")], reverse=True)
    for cp in checkpoints:
        path = os.path.join(CHECKPOINT_DIR, cp)
        if verify_checkpoint(path):
            return path
    return None

def recover_from_checkpoint(checkpoint_path: str) -> Optional[dict]:
    """Load and return the state from a valid checkpoint."""
    if not verify_checkpoint(checkpoint_path):
        return None
    with open(checkpoint_path, "r") as f:
        data = json.load(f)
    data.pop("hmac", None)
    return data

def auto_recover() -> Optional[dict]:
    """Automatically recover from the latest valid checkpoint."""
    latest = find_latest_valid_checkpoint()
    if latest:
        return recover_from_checkpoint(latest)
    return None
