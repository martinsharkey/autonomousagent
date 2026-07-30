import json
import os
import hmac
import hashlib
from pathlib import Path

CHECKPOINT_DIR = Path("checkpoints")
SECRET_KEY = os.environ.get("HMAC_SECRET", "default-secret")

def _compute_hmac(data: bytes) -> str:
    return hmac.new(SECRET_KEY.encode(), data, hashlib.sha256).hexdigest()

def validate_checkpoint(path: Path) -> bool:
    """Validate checkpoint file integrity using HMAC and JSON schema."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        data = json.loads(raw)
        if "hmac" not in data or "state" not in data:
            return False
        expected_hmac = _compute_hmac(json.dumps(data["state"], sort_keys=True).encode())
        if not hmac.compare_digest(data["hmac"], expected_hmac):
            return False
        # Basic schema check: state must be a dict with required keys
        required_keys = ["agent_id", "timestamp", "memory"]
        for key in required_keys:
            if key not in data["state"]:
                return False
        return True
    except (json.JSONDecodeError, KeyError, TypeError):
        return False

def recover_latest_valid() -> dict | None:
    """Find and return the most recent valid checkpoint state."""
    if not CHECKPOINT_DIR.exists():
        return None
    checkpoints = sorted(CHECKPOINT_DIR.glob("checkpoint_*.json"), reverse=True)
    for cp in checkpoints:
        if validate_checkpoint(cp):
            with open(cp, "r") as f:
                data = json.load(f)
            return data["state"]
    return None

def recover_and_restore() -> bool:
    """Attempt to recover state from the latest valid checkpoint. Returns True on success."""
    state = recover_latest_valid()
    if state is None:
        return False
    # Write recovered state to a known location for the agent loop to pick up
    recovery_path = Path("recovered_state.json")
    with open(recovery_path, "w") as f:
        json.dump(state, f, indent=2)
    return True

if __name__ == "__main__":
    success = recover_and_restore()
    print(json.dumps({"recovered": success}))
