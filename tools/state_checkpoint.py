import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

class StateCheckpointManager:
    def __init__(self, checkpoint_dir="checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.current_checkpoint = None

    def generate_checkpoint_id(self, state_data):
        """Generate a unique ID for a checkpoint based on state data."""
        state_str = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()

    def save_checkpoint(self, state_data, metadata=None):
        """Save a checkpoint of the current state with optional metadata."""
        checkpoint_id = self.generate_checkpoint_id(state_data)
        timestamp = datetime.utcnow().isoformat()
        checkpoint_filename = f"checkpoint_{checkpoint_id}_{timestamp}.json"
        checkpoint_path = self.checkpoint_dir / checkpoint_filename

        checkpoint_data = {
            "state": state_data,
            "metadata": metadata or {},
            "timestamp": timestamp,
            "checkpoint_id": checkpoint_id
        }

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint_data, f, indent=2)

        self.current_checkpoint = checkpoint_path
        return checkpoint_path

    def verify_checkpoint(self, checkpoint_path):
        """Verify the integrity of a checkpoint file."""
        try:
            with open(checkpoint_path, "r") as f:
                checkpoint_data = json.load(f)

            # Recompute the checkpoint ID to verify integrity
            state_str = json.dumps(checkpoint_data["state"], sort_keys=True)
            expected_id = hashlib.sha256(state_str.encode()).hexdigest()

            if checkpoint_data["checkpoint_id"] != expected_id:
                return False, "Checkpoint data corrupted or tampered with"

            return True, "Checkpoint verified"
        except Exception as e:
            return False, f"Verification failed: {str(e)}"

    def list_checkpoints(self):
        """List all available checkpoints."""
        checkpoints = []
        for file in self.checkpoint_dir.glob("checkpoint_*.json"):
            try:
                with open(file, "r") as f:
                    checkpoint_data = json.load(f)
                checkpoints.append({
                    "path": str(file),
                    "timestamp": checkpoint_data["timestamp"],
                    "checkpoint_id": checkpoint_data["checkpoint_id"],
                    "metadata": checkpoint_data.get("metadata", {})
                })
            except Exception:
                continue
        return sorted(checkpoints, key=lambda x: x["timestamp"], reverse=True)

    def recover_from_checkpoint(self, checkpoint_path=None):
        """Recover state from a checkpoint. If no path is provided, use the latest valid checkpoint."""
        if checkpoint_path is None:
            checkpoints = self.list_checkpoints()
            if not checkpoints:
                return None, "No checkpoints available"
            checkpoint_path = checkpoints[0]["path"]

        is_valid, message = self.verify_checkpoint(checkpoint_path)
        if not is_valid:
            return None, message

        try:
            with open(checkpoint_path, "r") as f:
                checkpoint_data = json.load(f)
            return checkpoint_data["state"], "Recovery successful"
        except Exception as e:
            return None, f"Recovery failed: {str(e)}"

    def cleanup_old_checkpoints(self, max_checkpoints=5):
        """Clean up old checkpoints, keeping only the most recent ones."""
        checkpoints = self.list_checkpoints()
        if len(checkpoints) > max_checkpoints:
            for checkpoint in checkpoints[max_checkpoints:]:
                try:
                    os.remove(checkpoint["path"])
                except Exception:
                    continue
