import json
import os
import hmac
import hashlib
from typing import Optional, Any

CHECKPOINT_DIR = "checkpoints"
HMAC_KEY = os.environ.get("HMAC_KEY", "default-dev-key").encode()

class Checkpointer:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    def save(self, state: dict) -> str:
        """Save state with HMAC integrity check."""
        state_copy = state.copy()
        state_copy["agent_id"] = self.agent_id
        state_copy["timestamp"] = __import__("time").time()
        # Compute HMAC over sorted JSON
        serialized = json.dumps(state_copy, sort_keys=True)
        state_copy["hmac"] = hmac.new(HMAC_KEY, serialized.encode(), hashlib.sha256).hexdigest()
        filename = f"{self.agent_id}_{state_copy['timestamp']}.json"
        path = os.path.join(CHECKPOINT_DIR, filename)
        with open(path, "w") as f:
            json.dump(state_copy, f, indent=2)
        return path

    def load_latest(self) -> Optional[dict]:
        """Load the latest valid checkpoint."""
        from tools.state_recovery import find_latest_valid_checkpoint, recover_from_checkpoint
        latest = find_latest_valid_checkpoint()
        if latest:
            return recover_from_checkpoint(latest)
        return None

    def list_checkpoints(self) -> list:
        """List all checkpoint files."""
        if not os.path.isdir(CHECKPOINT_DIR):
            return []
        return sorted([f for f in os.listdir(CHECKPOINT_DIR) if f.endswith(".json")], reverse=True)
