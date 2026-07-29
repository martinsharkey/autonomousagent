import json
import os
import hmac
import hashlib
from typing import Optional, Any
from pathlib import Path

CHECKPOINT_DIR = "checkpoints"
HMAC_KEY = os.environ.get("HMAC_KEY", "default-dev-key").encode()


class Checkpointer:
    """Durable checkpointer for council state."""
    
    def __init__(self, agent_id: str = "council"):
        self.agent_id = agent_id
        self.db_path = Path(CHECKPOINT_DIR)
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    def save(self, state: dict) -> str:
        """Save state with HMAC integrity check."""
        state_copy = state.copy()
        state_copy["agent_id"] = self.agent_id
        state_copy["timestamp"] = __import__("time").time()
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

    def list_threads(self) -> list:
        """List active checkpointer threads."""
        checkpoints = self.list_checkpoints()
        threads = []
        seen = set()
        for name in checkpoints:
            thread_id = name.split("_")[0]
            if thread_id not in seen:
                seen.add(thread_id)
                threads.append(thread_id)
        return threads


_checkpointer = Checkpointer()


def get_checkpointer() -> Checkpointer:
    return _checkpointer
