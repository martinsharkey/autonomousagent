import json
import hmac
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_FILE = CHECKPOINT_DIR / "agent_state.json"
HMAC_KEY = b"agent-state-recovery-key"  # In production, load from secure config

def verify_checkpoint_integrity() -> bool:
    """Verify the checkpoint file exists, has valid JSON, correct HMAC, and expected schema."""
    if not CHECKPOINT_FILE.exists():
        logger.warning("No checkpoint file found.")
        return False
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Checkpoint file corrupt: {e}")
        return False
    # Verify HMAC
    stored_hmac = data.pop("hmac", None)
    if stored_hmac is None:
        logger.error("Checkpoint missing HMAC.")
        return False
    computed_hmac = hmac.new(HMAC_KEY, json.dumps(data, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(stored_hmac, computed_hmac):
        logger.error("Checkpoint HMAC mismatch.")
        return False
    # Verify schema version
    if data.get("schema_version") != 1:
        logger.error(f"Unsupported schema version: {data.get('schema_version')}")
        return False
    # Verify timestamp freshness (within 24 hours)
    import time
    ts = data.get("timestamp", 0)
    if time.time() - ts > 86400:
        logger.warning("Checkpoint is older than 24 hours.")
        # Still valid, but warn
    logger.info("Checkpoint integrity verified.")
    return True

def recover_from_checkpoint() -> Optional[Dict[str, Any]]:
    """Load and return the checkpoint state if valid, else None."""
    if not verify_checkpoint_integrity():
        return None
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
        data.pop("hmac", None)
        logger.info("Recovered state from checkpoint.")
        return data
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        return None

def save_checkpoint(state: Dict[str, Any]) -> bool:
    """Save state with HMAC and schema version."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    import time
    state["timestamp"] = time.time()
    state["schema_version"] = 1
    hmac_val = hmac.new(HMAC_KEY, json.dumps(state, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    state["hmac"] = hmac_val
    try:
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(state, f, indent=2)
        logger.info("Checkpoint saved.")
        return True
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")
        return False
