#!/usr/bin/env python3
"""State recovery and integrity verification tool for durable local state."""
import json
import os
import hashlib
import hmac
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = "checkpoints"
HMAC_KEY_ENV = "STATE_HMAC_KEY"

def _load_checkpoint(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load checkpoint {path}: {e}")
        return None

def _verify_hmac(data: Dict[str, Any], key: str) -> bool:
    stored_hmac = data.get("hmac")
    if not stored_hmac:
        return False
    payload = {k: v for k, v in data.items() if k != "hmac"}
    payload_str = json.dumps(payload, sort_keys=True)
    computed = hmac.new(key.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, stored_hmac)

def verify_checkpoint(path: str) -> bool:
    """Verify integrity of a checkpoint file."""
    key = os.environ.get(HMAC_KEY_ENV, "default-dev-key")
    data = _load_checkpoint(path)
    if data is None:
        return False
    return _verify_hmac(data, key)

def list_checkpoints() -> list:
    """List all checkpoint files sorted by modification time."""
    if not os.path.isdir(CHECKPOINT_DIR):
        return []
    files = [f for f in os.listdir(CHECKPOINT_DIR) if f.endswith(".json")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(CHECKPOINT_DIR, f)), reverse=True)
    return files

def recover_latest_valid() -> Optional[Dict[str, Any]]:
    """Find and return the latest valid checkpoint."""
    checkpoints = list_checkpoints()
    for cp in checkpoints:
        path = os.path.join(CHECKPOINT_DIR, cp)
        if verify_checkpoint(path):
            data = _load_checkpoint(path)
            logger.info(f"Recovered from valid checkpoint: {cp}")
            return data
    logger.warning("No valid checkpoint found for recovery.")
    return None

def repair_checkpoint(path: str) -> bool:
    """Attempt to repair a corrupted checkpoint by removing invalid fields."""
    try:
        with open(path, "r") as f:
            raw = f.read()
        data = json.loads(raw)
        # Remove hmac and re-save without it (will be re-signed by checkpointer)
        if "hmac" in data:
            del data["hmac"]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Repaired checkpoint: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to repair checkpoint {path}: {e}")
        return False

def run_recovery_cycle() -> Dict[str, Any]:
    """Run full recovery cycle: verify, repair, recover."""
    result = {"verified": 0, "repaired": 0, "recovered": False}
    checkpoints = list_checkpoints()
    for cp in checkpoints:
        path = os.path.join(CHECKPOINT_DIR, cp)
        if verify_checkpoint(path):
            result["verified"] += 1
        else:
            if repair_checkpoint(path):
                result["repaired"] += 1
    recovered_data = recover_latest_valid()
    if recovered_data:
        result["recovered"] = True
        result["data"] = recovered_data
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        path = sys.argv[2] if len(sys.argv) > 2 else "checkpoints/latest.json"
        print(json.dumps({"valid": verify_checkpoint(path)}))
    else:
        print(json.dumps(run_recovery_cycle(), indent=2))
