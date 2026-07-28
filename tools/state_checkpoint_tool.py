import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional

class StateCheckpointTool:
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.current_checkpoint = None
        self.last_valid_checkpoint = None

    def _generate_checkpoint_id(self, state: Dict[str, Any]) -> str:
        """Generate a unique ID for the checkpoint based on state content."""
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]

    def _validate_checkpoint(self, checkpoint_path: Path) -> bool:
        """Validate checkpoint integrity before recovery."""
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint = json.load(f)
            # Basic validation: ensure required fields exist
            if not all(k in checkpoint for k in ['state', 'timestamp', 'checkpoint_id']):
                return False
            # Validate checkpoint ID matches state content
            expected_id = self._generate_checkpoint_id(checkpoint['state'])
            if checkpoint['checkpoint_id'] != expected_id:
                return False
            return True
        except (json.JSONDecodeError, KeyError, IOError):
            return False

    def create_checkpoint(self, state: Dict[str, Any]) -> Optional[str]:
        """Create a new checkpoint with validation and error handling."""
        try:
            checkpoint_id = self._generate_checkpoint_id(state)
            checkpoint_path = self.checkpoint_dir / f"checkpoint_{checkpoint_id}.json"
            
            checkpoint = {
                'state': state,
                'timestamp': time.time(),
                'checkpoint_id': checkpoint_id
            }
            
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint, f)
            
            self.current_checkpoint = checkpoint_id
            self.last_valid_checkpoint = checkpoint_id
            return checkpoint_id
        except Exception as e:
            print(f"[StateCheckpointTool] Failed to create checkpoint: {e}")
            return None

    def recover_last_valid_state(self) -> Optional[Dict[str, Any]]:
        """Recover the last valid state with phased recovery to avoid crashes."""
        # Phase 1: Find all valid checkpoints
        valid_checkpoints = []
        for checkpoint_file in self.checkpoint_dir.glob("checkpoint_*.json"):
            if self._validate_checkpoint(checkpoint_file):
                valid_checkpoints.append(checkpoint_file)
        
        if not valid_checkpoints:
            print("[StateCheckpointTool] No valid checkpoints found.")
            return None
        
        # Phase 2: Sort by timestamp (newest first)
        valid_checkpoints.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Phase 3: Attempt recovery from newest valid checkpoint
        for checkpoint_file in valid_checkpoints:
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                print(f"[StateCheckpointTool] Recovered state from {checkpoint_file.name}")
                self.current_checkpoint = checkpoint['checkpoint_id']
                self.last_valid_checkpoint = checkpoint['checkpoint_id']
                return checkpoint['state']
            except Exception as e:
                print(f"[StateCheckpointTool] Failed to recover from {checkpoint_file.name}: {e}")
                continue
        
        print("[StateCheckpointTool] All valid checkpoints failed recovery.")
        return None

    def cleanup_old_checkpoints(self, max_checkpoints: int = 5):
        """Clean up old checkpoints to prevent disk bloat."""
        checkpoint_files = list(self.checkpoint_dir.glob("checkpoint_*.json"))
        if len(checkpoint_files) > max_checkpoints:
            checkpoint_files.sort(key=lambda x: os.path.getmtime(x))
            for old_file in checkpoint_files[:-max_checkpoints]:
                try:
                    old_file.unlink()
                except Exception as e:
                    print(f"[StateCheckpointTool] Failed to cleanup {old_file.name}: {e}")

# Example usage:
# tool = StateCheckpointTool()
# tool.create_checkpoint({'key': 'value'})
# recovered_state = tool.recover_last_valid_state()
